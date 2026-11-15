// SPDX-License-Identifier: GPL-2.0-or-later
#include <chrono>
#include <cstdio>
#include <string>
#include <httplib.h>
#include "core/libraries/network/http_timeouts.h"
int main(int argc, char** argv) {
    if(argc!=4) return 2;
    const std::string mode=argv[3];
    httplib::Client client(argv[1]);
    client.enable_server_certificate_verification(true);
    client.enable_server_hostname_verification(true);
    if(mode!="untrusted") client.set_ca_cert_path(argv[2]);
    const auto budgets=Libraries::Http::Timeouts::Configure(client,1000000,mode=="read" ? 1000000 : 2000000,2000000,
                                                          mode!="raw");
    const auto started=std::chrono::steady_clock::now();
    const auto result=client.Get("/probe");
    const auto ms=std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now()-started).count();
    std::printf("TLS mode=%s budget=%llds elapsed=%lldms status=%d error=%s\n",mode.c_str(),
                static_cast<long long>(budgets.connect.count()),static_cast<long long>(ms),
                result ? result->status : 0,httplib::to_string(result.error()).c_str());
    if(mode=="read") return !result && result.error()==httplib::Error::Read &&
        budgets.receive==std::chrono::seconds(1) && ms<5000 ? 0 : 1;
    if(mode=="raw") return !result && result.error()==httplib::Error::SSLConnection ? 0 : 1;
    if(mode=="untrusted") return !result && result.error()==httplib::Error::SSLServerVerification ? 0 : 1;
    if(mode=="hostname") return !result && result.error()==httplib::Error::SSLServerHostnameVerification ? 0 : 1;
    if(!result || result->status!=200 || result->body!="verified-local-tls") return 1;
    if(mode=="fixed" && ms<1500) return 1;
    if(mode=="fast" && ms>=5000) return 1;
    return 0;
}
