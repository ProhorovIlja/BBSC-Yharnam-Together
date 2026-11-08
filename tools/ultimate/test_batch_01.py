# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline source integrity checks for Ultimate B01. Never builds or runs the game.

The immutable Git blob pins protect the 9-file coherent GPU patch from partial
cherry-picks and accidental update drift. Passing this does NOT demonstrate
shader compilation, driver safety, game rendering or five-player gameplay.
"""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tools/ultimate/batch_01_manifest.json"


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def file_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class BatchOneSourceEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.gpu, cls.auth = cls.plan["modules"]

    def test_manifest_has_correct_provenance_and_no_release_claim(self):
        self.assertEqual(self.plan["schema"], "bbsc-ultimate-batch-v1")
        self.assertEqual(self.plan["batch_id"], "B01-2026-11-08")
        self.assertTrue(self.plan["no_automatic_deploy"])
        self.assertTrue(self.plan["no_game_assets"])
        self.assertIn("NOT_RELEASE_READY", self.plan["disposition"])
        self.assertEqual(self.gpu["head_sha"], "7a8c6afb1cdfcb3a0c71c0498a3ad3da4e6de4cf")
        self.assertEqual(self.gpu["pull_request"], 543)
        self.assertEqual(self.auth["pull_request"], 27)
        self.assertEqual(len(self.gpu["expected_git_blobs"]), 9)
        self.assertTrue(self.gpu["pending"])
        self.assertTrue(self.auth["pending"])
        self.assertGreaterEqual(len(self.plan["pending_evaluations"]), 3)

    def test_all_nine_gpu_files_are_exact_upstream_source_blobs(self):
        for path, expected_sha in self.gpu["expected_git_blobs"].items():
            with self.subTest(path=path):
                self.assertTrue(path.startswith("bbport/gpu/shadps4/"))
                self.assertRegex(expected_sha, r"^[a-f0-9]{40}$")
                full = ROOT / path
                self.assertTrue(full.is_file())
                self.assertEqual(git_blob_sha(full.read_bytes()), expected_sha,
                                 "A GPU file drifted from the pinned coherent upstream patch")

    def test_tlscopy_preserves_source_pins_and_windows_fixture(self):
        for path, sha in self.auth["expected_git_blobs"].items():
            with self.subTest(path=path):
                self.assertEqual(git_blob_sha((ROOT / path).read_bytes()), sha)
        test = file_text("bbport/tests/test_launcher_auth.py")
        self.assertIn("BBSC_TEST_OPENSSL", test,
                      "Do not overwrite the Windows runner's fixture path support")
        self.assertIn("test_tls_failure_explains_which_data_were_not_sent_in_en_and_ru", test)
        self.assertIn("import bbport_lang_auth as lang_auth", test)

    def test_gpu_routes_all_describe_null_vertices_identically(self):
        root = "bbport/gpu/shadps4/"
        fetch = file_text(root + "shader_recompiler/frontend/fetch_shader.h")
        self.assertIn("BB_NULL_VERTEX_INPUT", fetch)
        self.assertIn("bool IsNullVertexInput(", fetch)
        self.assertIn("GetVertexInputFormat(", fetch)
        self.assertIn("DataFormat::Format32_32_32_32", fetch)
        self.assertIn("NumberFormat::Float, 0", fetch)
        translate = file_text(root + "shader_recompiler/frontend/translate/translate.cpp")
        self.assertIn("if (IsNullVertexInput(buffer))", translate)
        self.assertIn("ir.Imm32(0.f)", translate)
        spirv = file_text(root + "shader_recompiler/backend/spirv/spirv_emit_context.cpp")
        self.assertIn("Gcn::GetVertexInputFormat(attrib.GetSharp(info))", spirv)
        self.assertIn("GetAttributeInfo(num_format", spirv)
        for path in (
            "video_core/renderer_vulkan/vk_draw_prep.cpp",
            "video_core/renderer_vulkan/vk_graphics_pipeline.cpp",
            "video_core/renderer_vulkan/vk_pipeline_cache.cpp",
            "video_core/renderer_vulkan/vk_rasterizer.cpp",
        ):
            with self.subTest(path=path):
                text = file_text(root + path)
                self.assertIn("GetVertexInputFormat(", text)
        raster = file_text(root + "video_core/renderer_vulkan/vk_rasterizer.cpp")
        self.assertIn("NoteNullVertexInputs", raster)
        self.assertIn("reports.fetch_add(1", raster)
        self.assertIn("reports.load(std::memory_order_relaxed) >= 8", raster)
        special = file_text(root + "shader_recompiler/specialization.h")
        self.assertIn("buffers.size() != other.buffers.size()", special)
        self.assertIn("images.size() != other.images.size()", special)
        self.assertIn("samplers.size() != other.samplers.size()", special)
        self.assertIn("fmasks.empty()", special)

    def test_gpu_cache_versions_invalidated_in_same_batch(self):
        src = file_text(
            "bbport/gpu/shadps4/video_core/renderer_vulkan/vk_pipeline_serialization.cpp")
        self.assertRegex(src, r"ShaderBinaryVersion\s*=\s*18u")
        self.assertRegex(src, r"PipelineKeyVersion\s*=\s*8u")
        # Changing a shader definition without bumping old caches risks reusing
        # shaders/pipelines built with the invalid vertex-input interpretation.
        self.assertIn("null vertex inputs", src)

    def test_never_pretend_source_integrity_means_runtime_validation(self):
        for m in self.plan["modules"]:
            self.assertIn("unverified", m["state"])
        self.assertIn("five-hunter", " ".join(self.plan["release_gates"]))
        self.assertEqual(self.plan["build_cadence"]["candidate_edits"],
                         "offline tests + source contract only")


if __name__ == "__main__":
    unittest.main()
