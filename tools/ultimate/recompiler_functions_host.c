/* Whole-function RcApi test host: original synthetic fixture only. No loader,
 * game memory, interpreter or production dispatch. GPL-2.0-or-later donor
 * interface: bloodborne-native/bbcpu src/recomp/rc.h (API4).
 */
#include "recomp/rc.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

extern const RcFunction *bb_recomp_init(const RcApi *, size_t *);
static const RcFunction *functions;
static const uint64_t base = UINT64_C(0x10000000), done = UINT64_C(0x1234abcd);
static unsigned calls, tails, host_calls, reentries, cases;
static uint64_t variation, negative_rip;

static void require(int condition) { if (!condition) exit(90); }
static RcFn lookup(uint64_t target) {
    /* Exact allowlist; a range check alone would admit holes/negative fixtures. */
    for (size_t i=0; i<6; ++i)
        if (target == base + functions[i].offset) return functions[i].fn;
    exit(81);
}
static uint64_t forbidden_step(BbCpu *c) {
    require(negative_rip && c->rip==negative_rip);
    exit(83);
}
static void forbidden_bail(BbCpu *c, uint64_t rsp) { (void)c; (void)rsp; exit(84); }
static void push_return(BbCpu *c, uint64_t next) {
    c->r[RSP] -= 8;
    rc_st(c->r[RSP], 8, next);
}
static void call(BbCpu *c, uint64_t target, uint64_t next) {
    ++calls;
    const uint64_t rsp = c->r[RSP];
    if (target == base + 0xf000) {
        ++host_calls;
        const unsigned regs[] = {RDI, RSI, RDX, RCX, R8, R9};
        uint64_t sum = 0;
        for (unsigned i=0; i<6; ++i) {
            require(c->r[regs[i]] == 11u*(i+1));
            sum += (i+1)*c->r[regs[i]];
        }
        /* CALL has not pushed its return yet. Stack arg1 is at pre-CALL rsp. */
        require(rc_ld(rsp,8)==77 && rc_ld(rsp+8,8)==88);
        sum += 7*rc_ld(rsp,8) + 8*rc_ld(rsp+8,8);
        push_return(c, next);
        c->rip = base + 0x1000;
        lookup(c->rip)(c);
        ++reentries;
        require(c->rip==next && c->r[RSP]==rsp && c->r[RAX]==33);
        c->r[RAX] += sum;
    } else {
        RcFn fn = lookup(target);
        push_return(c, next);
        c->rip = target;
        fn(c);
    }
    require(c->r[RSP]==rsp && c->rip==next);
}
static void tail(BbCpu *c) { ++tails; lookup(c->rip)(c); }

static void one(unsigned slot, uint64_t target, uint64_t expected, unsigned tcb_case) {
    _Alignas(16) uint64_t stack[64];
    for (unsigned i=0; i<64; ++i) stack[i] = UINT64_C(0xbad0cafe01234567);
    BbCpu c = {0};
    for (unsigned i=0; i<16; ++i) c.r[i]=UINT64_C(0x55000000)+i;
    c.r[RDI]=11; c.r[RSI]=22; c.r[RDX]=33; c.r[RCX]=44; c.r[R8]=55; c.r[R9]=66;
    if (target!=base+0xf000) { c.r[RDI]+=variation; c.r[RSI]^=variation; }
    c.r[RSP]=(uintptr_t)&stack[32];
    c.r[RAX]=target; c.tcb=UINT64_C(0xfedcba9876543210)^variation;
    c.rip=base+functions[slot].offset;
    stack[32]=done;
    const uint64_t entry=c.r[RSP];
    functions[slot].fn(&c);
    require(c.r[RSP]==entry+8 && c.rip==done);
    require((tcb_case==2 ? c.r[RBX] : c.r[RAX])==expected);
    if (tcb_case!=2) require(c.r[RBX]==UINT64_C(0x55000003));
    require(c.r[RBP]==UINT64_C(0x55000005));
    for (unsigned i=12;i<16;++i) require(c.r[i]==UINT64_C(0x55000000)+i);
    require(stack[0]==UINT64_C(0xbad0cafe01234567) && stack[63]==stack[0]);
    ++cases;
}

int main(int argc, char **argv) {
    const RcApi api={.version=BB_RECOMP_API_VERSION,.image_base=UINT64_C(0x10000000),
                     .step=forbidden_step,.call=call,.tail=tail,.bail=forbidden_bail,.trace=NULL};
    size_t count=0;
    functions=bb_recomp_init(&api,&count);
    require(functions && count==9);
    for (size_t i=0;i<count;++i) {
        require(functions[i].offset==0x1000+0x20*i && functions[i].fn && functions[i].direct);
        require(*functions[i].direct==NULL);
    }
    if (argc>1) {
        if (!strcmp(argv[1],"unknown")) one(2,base+0xdead,0,0);
        else if (!strcmp(argv[1],"fs_nonzero")) { negative_rip=base+0x10e0; one(7,0,0,0); }
        else if (!strcmp(argv[1],"syscall")) { negative_rip=base+0x10c0; one(6,0,0,0); }
        else return 80;
        return 91;
    }
    for (unsigned direct=0;direct<2;++direct) {
        for (size_t i=0;i<6;++i) *functions[i].direct=direct ? functions[i].fn : NULL;
        for(unsigned trial=0;trial<1000;++trial) {
            variation=UINT64_C(0x9e3779b97f4a7c15)*trial;
            const uint64_t sum=(11+variation)+(22^variation);
            const uint64_t tcb=UINT64_C(0xfedcba9876543210)^variation;
            one(0,0,sum,0);
            one(1,0,sum+3,0);
            one(2,base+0x1000,sum+5,0);
            one(3,0,sum,0);
            one(4,0,tcb,1);
            one(5,0,tcb,2);
            one(8,base+0xf000,2282,0);
        }
    }
    require(cases==14000 && calls==5000 && tails==1000 && host_calls==2000 && reentries==2000);
    printf("{\"function_cases\":%u,\"call_callbacks\":%u,\"tail_callbacks\":%u,"
           "\"host_callbacks\":%u,\"reentrant_calls\":%u,\"step_callbacks\":0,"
           "\"bail_callbacks\":0,\"direct_slots_on_and_off\":true}\n",
           cases,calls,tails,host_calls,reentries);
    return 0;
}
