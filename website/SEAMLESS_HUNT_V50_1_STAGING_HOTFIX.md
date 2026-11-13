# V50.1 staging hotfix

[Staging archive with source and tests](https://drive.google.com/file/d/1dXHITHwZ_j0kLOpE2DciYsnONlzZqkmj/view). Run the updated `stage_v50.py` against the unchanged V49 staging tree, with a new sibling destination. The former whole-file text match could count duplicated text in export metadata or scripts. The new parser scopes the copy edit to a paragraph after the visible Install heading and before the next section. If no unique intro matches, it leaves that text alone and completes the other website edits. No production deployment.

Reproduced the original error on a V49 export fixture with one visible intro and duplicate metadata and script text. V50.1 staged that fixture, rewrote only the intended paragraph, preserved the Download footer GitHub link and all four release asset selectors, and also staged an export with no dated intro. Four focused regression tests passed.
