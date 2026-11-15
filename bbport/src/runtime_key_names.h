/* SPDX-License-Identifier: GPL-2.0-or-later */
#pragma once
#include <SDL3/SDL.h>

/* Commas separate alternatives in bbport.ini. Use a delimiter-free spelling
   for that physical key at every capture/serialization boundary. */
static inline SDL_Scancode bbport_key_from_binding(const char *name) {
    return SDL_strcasecmp(name,"Comma")==0 ? SDL_SCANCODE_COMMA : SDL_GetScancodeFromName(name);
}
static inline const char *bbport_key_binding_name(SDL_Scancode code) {
    return code==SDL_SCANCODE_COMMA ? "Comma" : SDL_GetScancodeName(code);
}
