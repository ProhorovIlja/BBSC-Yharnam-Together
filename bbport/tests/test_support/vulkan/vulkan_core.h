// SPDX-License-Identifier: GPL-2.0-or-later
// TEST-ONLY compile stub: production GpuMemory uses Vulkan only as opaque
// VkBuffer and VkDeviceAddress types. No GPU/driver functions are mocked.
#pragma once
#include <stdint.h>
typedef struct VkBuffer_T* VkBuffer;
typedef uint64_t VkDeviceAddress;
#ifndef VK_NULL_HANDLE
#define VK_NULL_HANDLE nullptr
#endif
