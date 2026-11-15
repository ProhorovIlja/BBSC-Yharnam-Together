cmake_minimum_required(VERSION 3.20)
project(ultimate_copy_safety LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
enable_testing()
add_custom_command(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/copy_hle.inc
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/extract_hle.py
          ${CMAKE_CURRENT_SOURCE_DIR}/../../../bbport/gpu/shadps4/video_core/renderer_vulkan/vk_shader_hle.cpp
          ${CMAKE_CURRENT_BINARY_DIR}/copy_hle.inc
  DEPENDS extract_hle.py ../../../bbport/gpu/shadps4/video_core/renderer_vulkan/vk_shader_hle.cpp)
add_executable(copy_ranges ../../../bbport/tests/test_copy_shader.cpp)
target_include_directories(copy_ranges PRIVATE ../../../bbport)
add_executable(copy_hle ../../../bbport/tests/copy_hle_harness.cpp ${CMAKE_CURRENT_BINARY_DIR}/copy_hle.inc)
target_include_directories(copy_hle PRIVATE ../../../bbport/gpu/shim ${CMAKE_CURRENT_BINARY_DIR})
foreach(target copy_ranges copy_hle)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /WX)
    target_compile_definitions(${target} PRIVATE _CRT_SECURE_NO_WARNINGS)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Werror)
  endif()
  add_test(NAME ${target} COMMAND ${target})
endforeach()
