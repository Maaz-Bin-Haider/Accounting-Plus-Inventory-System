import re
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.template import engines
from django.test import SimpleTestCase


class TemplateAndStaticAssetSmokeTests(SimpleTestCase):
    """Keep the complete project template/static dependency graph loadable."""

    template_root = Path(settings.BASE_DIR) / "templates"
    static_tag_pattern = re.compile(
        r"\{%\s*static\s+['\"]([^'\"]+)['\"]\s*%\}"
    )

    @classmethod
    def project_templates(cls):
        return sorted(cls.template_root.rglob("*.html"))

    def test_every_project_template_compiles(self):
        template_engine = engines["django"]
        templates = self.project_templates()
        self.assertTrue(templates, "No project HTML templates were discovered")

        for template_path in templates:
            template_name = template_path.relative_to(self.template_root).as_posix()
            with self.subTest(template=template_name):
                template_engine.get_template(template_name)

    def test_every_template_static_reference_resolves_to_a_nonempty_file(self):
        references = {}
        for template_path in self.project_templates():
            source = template_path.read_text(encoding="utf-8")
            for asset in self.static_tag_pattern.findall(source):
                references.setdefault(asset, []).append(
                    template_path.relative_to(self.template_root).as_posix()
                )

        self.assertTrue(references, "No template static references were discovered")
        for asset, templates in sorted(references.items()):
            with self.subTest(asset=asset, templates=templates):
                resolved = finders.find(asset)
                self.assertIsNotNone(
                    resolved,
                    f"Static asset {asset!r} referenced by {templates} was not found",
                )
                self.assertGreater(
                    Path(resolved).stat().st_size,
                    0,
                    f"Static asset {asset!r} referenced by {templates} is empty",
                )

    def test_custom_css_and_javascript_assets_are_nonempty(self):
        custom_static_root = Path(settings.BASE_DIR) / "static"
        assets = sorted(
            path
            for extension in ("*.css", "*.js")
            for path in custom_static_root.rglob(extension)
            if "admin" not in path.relative_to(custom_static_root).parts
        )
        self.assertTrue(assets, "No custom CSS or JavaScript assets were discovered")
        for asset in assets:
            with self.subTest(asset=asset.relative_to(custom_static_root)):
                self.assertGreater(asset.stat().st_size, 0)
