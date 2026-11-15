/* Exercise the actual SDL capture utility with queued input and a dummy window. */
#define _POSIX_C_SOURCE 200809L
#define main bbport_capabilities_program_main
#include "../tools/gpu_capabilities.c"
#undef main
#include <assert.h>
#include <unistd.h>

static void capture_key(SDL_Scancode code, SDL_Keymod mods, const char *expected) {
    const bool initialized=SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMEPAD);
    if (!initialized) fprintf(stderr,"SDL input fixture: %s\n",SDL_GetError());
    assert(initialized);
    SDL_Event event={0};
    event.type=SDL_EVENT_KEY_DOWN;
    event.key.scancode=code;
    event.key.mod=mods;
    assert(SDL_PushEvent(&event));
    int output[2];
    assert(pipe(output)==0);
    fflush(stdout);
    const int saved=dup(STDOUT_FILENO);
    assert(saved>=0 && dup2(output[1],STDOUT_FILENO)>=0);
    close(output[1]);
    const int result=read_input("key");
    fflush(stdout);
    assert(dup2(saved,STDOUT_FILENO)>=0);
    close(saved);
    char text[128]={0};
    const ssize_t bytes=read(output[0],text,sizeof text-1);
    close(output[0]);
    assert(result==0 && bytes>0 && !strcmp(text,expected));
}

int main(void) {
    assert(setenv("SDL_VIDEODRIVER","dummy",1)==0);
    assert(setenv("SDL_RENDER_DRIVER","software",1)==0);
    capture_key(SDL_SCANCODE_F5,SDL_KMOD_NONE,"key F5\n");
    capture_key(SDL_SCANCODE_F5,SDL_KMOD_CTRL,"key Ctrl+F5\n");
    capture_key(SDL_SCANCODE_COMMA,SDL_KMOD_SHIFT|SDL_KMOD_CTRL|SDL_KMOD_ALT,
                "key Shift+Ctrl+Alt+Comma\n");
    puts("PASS: actual SDL keyboard capture retains event modifiers and delimiter-safe Comma");
}
