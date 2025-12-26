# tests/unit/cli/test_runner.py
# Unit tests for unified TailoringRunner class

import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from src.cli.runner import (
    TailoringMode,
    TailoringContext,
    ResumeContext,
    TailoringRunner,
    prepare_resume_context,
    build_tailoring_context,
    VALIDATION_REQUIREMENTS,
)
from src.cli.logic import ArgResolver
from src.config.settings import LoomSettings
from src.core.constants import RiskLevel, ValidationPolicy
from src.loom_io.types import Lines


# * Test TailoringMode enum values
class TestTailoringMode:
    def test_mode_values(self):
        assert TailoringMode.GENERATE.value == "generate"
        assert TailoringMode.APPLY.value == "apply"
        assert TailoringMode.TAILOR.value == "tailor"
        assert TailoringMode.PLAN.value == "plan"

    def test_mode_iteration(self):
        modes = list(TailoringMode)
        assert len(modes) == 4


# * Test TailoringContext dataclass
class TestTailoringContext:
    @pytest.fixture
    def mock_settings(self, tmp_path):
        return LoomSettings(
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            base_dir=str(tmp_path / ".loom"),
        )

    def test_context_defaults(self, mock_settings):
        ctx = TailoringContext(settings=mock_settings)
        assert ctx.resume is None
        assert ctx.job is None
        assert ctx.model is None
        assert ctx.edits_json is None
        assert ctx.output_resume is None
        assert ctx.sections_path is None
        assert ctx.risk == RiskLevel.MED
        assert ctx.on_error == ValidationPolicy.ASK
        assert ctx.preserve_formatting is True
        assert ctx.preserve_mode == "in_place"
        assert ctx.interactive is True

    def test_is_latex_property_tex(self, mock_settings):
        ctx = TailoringContext(settings=mock_settings, resume=Path("resume.tex"))
        assert ctx.is_latex is True

    def test_is_latex_property_tex_uppercase(self, mock_settings):
        ctx = TailoringContext(settings=mock_settings, resume=Path("resume.TEX"))
        assert ctx.is_latex is True

    def test_is_latex_property_docx(self, mock_settings):
        ctx = TailoringContext(settings=mock_settings, resume=Path("resume.docx"))
        assert ctx.is_latex is False

    def test_is_latex_property_none(self, mock_settings):
        ctx = TailoringContext(settings=mock_settings, resume=None)
        assert ctx.is_latex is False


# * Test ResumeContext dataclass
class TestResumeContext:

    def test_resume_context_defaults(self):
        lines: Lines = {1: "line 1", 2: "line 2"}
        ctx = ResumeContext(lines=lines)
        assert ctx.lines == lines
        assert ctx.job_text is None
        assert ctx.descriptor is None
        assert ctx.auto_sections_json is None
        assert ctx.template_notes == []
        assert ctx.sections_json_str is None

    def test_resume_context_full(self):
        lines: Lines = {1: "line 1"}
        ctx = ResumeContext(
            lines=lines,
            job_text="job text",
            descriptor=Mock(),
            auto_sections_json='{"sections": []}',
            template_notes=["note1", "note2"],
            sections_json_str='{"sections": []}',
        )
        assert ctx.job_text == "job text"
        assert ctx.auto_sections_json == '{"sections": []}'
        assert len(ctx.template_notes) == 2


# * Test VALIDATION_REQUIREMENTS mapping
class TestValidationRequirements:
    def test_generate_requirements(self):
        reqs = VALIDATION_REQUIREMENTS[TailoringMode.GENERATE]
        assert "resume" in reqs
        assert "job" in reqs
        assert "model" in reqs
        assert "output_resume" not in reqs
        assert "edits_json" not in reqs

    def test_apply_requirements(self):
        reqs = VALIDATION_REQUIREMENTS[TailoringMode.APPLY]
        assert "resume" in reqs
        assert "edits_json" in reqs
        assert "output_resume" in reqs
        assert "job" not in reqs
        assert "model" not in reqs

    def test_tailor_requirements(self):
        reqs = VALIDATION_REQUIREMENTS[TailoringMode.TAILOR]
        assert "resume" in reqs
        assert "job" in reqs
        assert "model" in reqs
        assert "output_resume" in reqs

    def test_plan_requirements(self):
        reqs = VALIDATION_REQUIREMENTS[TailoringMode.PLAN]
        assert "resume" in reqs
        assert "job" in reqs
        assert "model" in reqs
        assert "output_resume" not in reqs


# * Test build_tailoring_context factory function
class TestBuildTailoringContext:
    @pytest.fixture
    def mock_settings(self, tmp_path):
        return LoomSettings(
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            base_dir=str(tmp_path / ".loom"),
            model="default-model",
        )

    def test_build_context_with_provided_args(self, mock_settings):
        resolver = ArgResolver(mock_settings)
        ctx = build_tailoring_context(
            mock_settings,
            resolver,
            resume=Path("my_resume.docx"),
            job=Path("my_job.txt"),
            model="gpt-4o",
            edits_json=Path("edits.json"),
            risk=RiskLevel.HIGH,
            on_error=ValidationPolicy.FAIL_HARD,
            preserve_formatting=False,
            preserve_mode="rebuild",
            interactive=False,
        )

        assert ctx.resume == Path("my_resume.docx")
        assert ctx.job == Path("my_job.txt")
        assert ctx.model == "gpt-4o"
        assert ctx.edits_json == Path("edits.json")
        assert ctx.risk == RiskLevel.HIGH
        assert ctx.on_error == ValidationPolicy.FAIL_HARD
        assert ctx.preserve_formatting is False
        assert ctx.preserve_mode == "rebuild"
        assert ctx.interactive is False

    def test_build_context_with_defaults(self, mock_settings):
        resolver = ArgResolver(mock_settings)
        ctx = build_tailoring_context(mock_settings, resolver)

        # should use defaults from settings
        assert ctx.model == "default-model"
        assert ctx.risk == RiskLevel.MED
        assert ctx.on_error == ValidationPolicy.ASK
        assert ctx.preserve_formatting is True
        assert ctx.preserve_mode == "in_place"
        assert ctx.interactive is True


# * Test TailoringRunner validation logic
class TestTailoringRunnerValidation:
    @pytest.fixture
    def mock_settings(self, tmp_path):
        return LoomSettings(
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            base_dir=str(tmp_path / ".loom"),
        )

    def test_validate_generate_mode_success(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
        )
        runner = TailoringRunner(TailoringMode.GENERATE, ctx)
        # should not raise
        runner.validate()

    def test_validate_generate_mode_missing_resume(self, mock_settings):
        import typer

        ctx = TailoringContext(
            settings=mock_settings,
            resume=None,
            job=Path("job.txt"),
            model="gpt-4o",
        )
        runner = TailoringRunner(TailoringMode.GENERATE, ctx)
        with pytest.raises(typer.BadParameter, match="Resume path is required"):
            runner.validate()

    def test_validate_apply_mode_success(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            edits_json=Path("edits.json"),
            output_resume=Path("output.docx"),
        )
        runner = TailoringRunner(TailoringMode.APPLY, ctx)
        runner.validate()

    def test_validate_apply_mode_missing_edits(self, mock_settings):
        import typer

        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            edits_json=None,
            output_resume=Path("output.docx"),
        )
        runner = TailoringRunner(TailoringMode.APPLY, ctx)
        with pytest.raises(typer.BadParameter, match="Edits path is required"):
            runner.validate()

    def test_validate_tailor_mode_success(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
            output_resume=Path("output.docx"),
        )
        runner = TailoringRunner(TailoringMode.TAILOR, ctx)
        runner.validate()

    def test_validate_plan_mode_success(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
        )
        runner = TailoringRunner(TailoringMode.PLAN, ctx)
        runner.validate()


# * Test TailoringRunner step calculation logic
class TestTailoringRunnerStepCalculation:
    @pytest.fixture
    def mock_settings(self, tmp_path):
        return LoomSettings(
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            base_dir=str(tmp_path / ".loom"),
        )

    def test_calculate_steps_generate_base(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
        )
        runner = TailoringRunner(TailoringMode.GENERATE, ctx)
        assert runner.calculate_total_steps() == 4

    def test_calculate_steps_generate_with_sections(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
            sections_path=Path("sections.json"),
        )
        runner = TailoringRunner(TailoringMode.GENERATE, ctx)
        assert runner.calculate_total_steps() == 5  # 4 + 1 for sections

    def test_calculate_steps_apply_base(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            edits_json=Path("edits.json"),
            output_resume=Path("output.docx"),
        )
        runner = TailoringRunner(TailoringMode.APPLY, ctx)
        assert runner.calculate_total_steps() == 5

    def test_calculate_steps_apply_with_latex(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.tex"),
            edits_json=Path("edits.json"),
            output_resume=Path("output.tex"),
        )
        runner = TailoringRunner(TailoringMode.APPLY, ctx)
        assert runner.calculate_total_steps() == 6  # 5 + 1 for LaTeX

    def test_calculate_steps_apply_with_job(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            edits_json=Path("edits.json"),
            output_resume=Path("output.docx"),
        )
        runner = TailoringRunner(TailoringMode.APPLY, ctx)
        assert runner.calculate_total_steps() == 6  # 5 + 1 for optional job

    def test_calculate_steps_apply_full(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.tex"),
            job=Path("job.txt"),
            edits_json=Path("edits.json"),
            output_resume=Path("output.tex"),
            sections_path=Path("sections.json"),
        )
        runner = TailoringRunner(TailoringMode.APPLY, ctx)
        assert runner.calculate_total_steps() == 8  # 5 + 1 LaTeX + 1 job + 1 sections

    def test_calculate_steps_tailor_base(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
            output_resume=Path("output.docx"),
        )
        runner = TailoringRunner(TailoringMode.TAILOR, ctx)
        assert runner.calculate_total_steps() == 7

    def test_calculate_steps_tailor_with_latex(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.tex"),
            job=Path("job.txt"),
            model="gpt-4o",
            output_resume=Path("output.tex"),
        )
        runner = TailoringRunner(TailoringMode.TAILOR, ctx)
        assert runner.calculate_total_steps() == 8  # 7 + 1 for LaTeX

    def test_calculate_steps_plan_base(self, mock_settings):
        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
        )
        runner = TailoringRunner(TailoringMode.PLAN, ctx)
        assert runner.calculate_total_steps() == 5


# * Test prepare_resume_context function
class TestPrepareResumeContext:
    @pytest.fixture
    def mock_settings(self, tmp_path):
        return LoomSettings(
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            base_dir=str(tmp_path / ".loom"),
        )

    @pytest.fixture
    def mock_progress(self):
        progress = Mock()
        task = Mock()
        return progress, task

    @pytest.fixture
    def mock_ui(self):
        return Mock()

    @patch("src.cli.runner.load_resume_and_job")
    @patch("src.cli.runner.load_sections")
    def test_prepare_context_with_job(
        self,
        mock_load_sections,
        mock_load_resume_and_job,
        mock_settings,
        mock_ui,
        mock_progress,
    ):
        progress, task = mock_progress
        mock_load_resume_and_job.return_value = ({1: "line 1"}, "job text")
        mock_load_sections.return_value = None

        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
        )

        result = prepare_resume_context(ctx, mock_ui, progress, task, load_job=True)

        assert result.lines == {1: "line 1"}
        assert result.job_text == "job text"
        mock_load_resume_and_job.assert_called_once()

    @patch("src.cli.runner.read_resume")
    @patch("src.cli.runner.load_sections")
    def test_prepare_context_without_job(
        self,
        mock_load_sections,
        mock_read_resume,
        mock_settings,
        mock_ui,
        mock_progress,
    ):
        progress, task = mock_progress
        mock_read_resume.return_value = {1: "line 1"}
        mock_load_sections.return_value = None

        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=None,
        )

        result = prepare_resume_context(ctx, mock_ui, progress, task, load_job=False)

        assert result.lines == {1: "line 1"}
        assert result.job_text is None
        mock_read_resume.assert_called_once()

    @patch("src.cli.runner.read_resume")
    @patch("src.cli.runner.build_latex_context")
    @patch("src.cli.runner.load_sections")
    def test_prepare_context_latex_detection(
        self,
        mock_load_sections,
        mock_build_latex,
        mock_read_resume,
        mock_settings,
        mock_ui,
        mock_progress,
    ):
        progress, task = mock_progress
        mock_read_resume.return_value = {1: "\\documentclass"}
        mock_descriptor = Mock()
        mock_descriptor.id = "moderncv"
        mock_build_latex.return_value = (mock_descriptor, '{"sections": []}', ["note1"])
        mock_load_sections.return_value = None

        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.tex"),
            job=None,
        )

        result = prepare_resume_context(ctx, mock_ui, progress, task, load_job=False)

        assert result.descriptor == mock_descriptor
        assert result.auto_sections_json == '{"sections": []}'
        assert result.template_notes == ["note1"]
        mock_build_latex.assert_called_once()
        # verify LaTeX info was displayed
        mock_ui.print.assert_called()

    @patch("src.cli.runner.read_resume")
    @patch("src.cli.runner.load_sections")
    def test_prepare_context_explicit_sections(
        self,
        mock_load_sections,
        mock_read_resume,
        mock_settings,
        mock_ui,
        mock_progress,
    ):
        progress, task = mock_progress
        mock_read_resume.return_value = {1: "line 1"}
        mock_load_sections.return_value = '{"sections": [{"name": "EXP"}]}'

        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            sections_path=Path("sections.json"),
        )

        result = prepare_resume_context(ctx, mock_ui, progress, task, load_job=False)

        assert result.sections_json_str == '{"sections": [{"name": "EXP"}]}'
        mock_load_sections.assert_called_once()


# * Test TailoringRunner execution methods
class TestTailoringRunnerExecution:
    @pytest.fixture
    def mock_settings(self, tmp_path):
        settings = LoomSettings(
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            base_dir=str(tmp_path / ".loom"),
        )
        # create directories
        Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
        Path(settings.base_dir).mkdir(parents=True, exist_ok=True)
        return settings

    @patch("src.cli.runner.setup_ui_with_progress")
    @patch("src.cli.runner.prepare_resume_context")
    @patch("src.cli.runner.generate_edits_core")
    @patch("src.cli.runner.persist_edits_json")
    @patch("src.cli.runner.report_result")
    def test_run_generate_mode(
        self,
        mock_report,
        mock_persist,
        mock_generate,
        mock_prepare,
        mock_setup,
        mock_settings,
    ):
        # setup mocks
        mock_ui = Mock()
        mock_progress = Mock()
        mock_task = Mock()
        mock_setup.return_value.__enter__ = Mock(
            return_value=(mock_ui, mock_progress, mock_task)
        )
        mock_setup.return_value.__exit__ = Mock(return_value=False)

        mock_prepare.return_value = ResumeContext(
            lines={1: "line 1"},
            job_text="job text",
        )
        mock_generate.return_value = {"version": 1, "ops": []}

        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
            edits_json=Path("edits.json"),
        )
        runner = TailoringRunner(TailoringMode.GENERATE, ctx)
        runner.run()

        mock_generate.assert_called_once()
        mock_persist.assert_called_once()
        mock_report.assert_called_once_with("edits", edits_path=Path("edits.json"))

    @patch("src.cli.runner.setup_ui_with_progress")
    @patch("src.cli.runner.read_resume")
    @patch("src.cli.runner.load_edits_json")
    @patch("src.cli.runner.apply_edits_core")
    @patch("src.cli.runner.write_output_with_diff")
    @patch("src.cli.runner.report_result")
    def test_run_apply_mode(
        self,
        mock_report,
        mock_write,
        mock_apply,
        mock_load_edits,
        mock_read_resume,
        mock_setup,
        mock_settings,
    ):
        # setup mocks
        mock_ui = Mock()
        mock_progress = Mock()
        mock_task = Mock()
        mock_setup.return_value.__enter__ = Mock(
            return_value=(mock_ui, mock_progress, mock_task)
        )
        mock_setup.return_value.__exit__ = Mock(return_value=False)

        # _run_apply reads resume directly (not via prepare_resume_context)
        mock_read_resume.return_value = {1: "line 1"}
        mock_load_edits.return_value = {"version": 1, "ops": []}
        mock_apply.return_value = {1: "new line 1"}

        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            edits_json=Path("edits.json"),
            output_resume=Path("output.docx"),
        )
        runner = TailoringRunner(TailoringMode.APPLY, ctx)
        runner.run()

        mock_read_resume.assert_called_once()
        mock_apply.assert_called_once()
        mock_write.assert_called_once()
        mock_report.assert_called_once()

    @patch("src.cli.runner.setup_ui_with_progress")
    @patch("src.cli.runner.prepare_resume_context")
    @patch("src.cli.runner.generate_edits_core")
    @patch("src.cli.runner.persist_edits_json")
    @patch("src.cli.runner.apply_edits_core")
    @patch("src.cli.runner.write_output_with_diff")
    @patch("src.cli.runner.report_result")
    def test_run_tailor_mode(
        self,
        mock_report,
        mock_write,
        mock_apply,
        mock_persist,
        mock_generate,
        mock_prepare,
        mock_setup,
        mock_settings,
    ):
        # setup mocks
        mock_ui = Mock()
        mock_progress = Mock()
        mock_task = Mock()
        mock_setup.return_value.__enter__ = Mock(
            return_value=(mock_ui, mock_progress, mock_task)
        )
        mock_setup.return_value.__exit__ = Mock(return_value=False)

        mock_prepare.return_value = ResumeContext(
            lines={1: "line 1"},
            job_text="job text",
        )
        mock_generate.return_value = {"version": 1, "ops": []}
        mock_apply.return_value = {1: "new line 1"}

        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
            edits_json=Path("edits.json"),
            output_resume=Path("output.docx"),
        )
        runner = TailoringRunner(TailoringMode.TAILOR, ctx)
        runner.run()

        mock_generate.assert_called_once()
        mock_persist.assert_called_once()
        mock_apply.assert_called_once()
        mock_write.assert_called_once()
        mock_report.assert_called_once()

    @patch("src.cli.runner.setup_ui_with_progress")
    @patch("src.cli.runner.prepare_resume_context")
    @patch("src.cli.runner.generate_edits_core")
    @patch("src.cli.runner.persist_edits_json")
    @patch("src.cli.runner.ensure_parent")
    @patch("src.cli.runner.report_result")
    def test_run_plan_mode(
        self,
        mock_report,
        mock_ensure,
        mock_persist,
        mock_generate,
        mock_prepare,
        mock_setup,
        mock_settings,
    ):
        # setup mocks
        mock_ui = Mock()
        mock_progress = Mock()
        mock_task = Mock()
        mock_setup.return_value.__enter__ = Mock(
            return_value=(mock_ui, mock_progress, mock_task)
        )
        mock_setup.return_value.__exit__ = Mock(return_value=False)

        mock_prepare.return_value = ResumeContext(
            lines={1: "line 1"},
            job_text="job text",
        )
        mock_generate.return_value = {"version": 1, "ops": []}

        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
            edits_json=Path("edits.json"),
        )
        runner = TailoringRunner(TailoringMode.PLAN, ctx)
        runner.run()

        mock_generate.assert_called_once()
        mock_persist.assert_called_once()
        mock_ensure.assert_called()  # plan file parent dir
        mock_report.assert_called_once_with(
            "plan", settings=mock_settings, edits_path=Path("edits.json")
        )

    @patch("src.cli.runner.setup_ui_with_progress")
    @patch("src.cli.runner.prepare_resume_context")
    @patch("src.cli.runner.generate_edits_core")
    def test_run_generate_mode_failure(
        self, mock_generate, mock_prepare, mock_setup, mock_settings
    ):
        from src.core.exceptions import EditError

        # setup mocks
        mock_ui = Mock()
        mock_progress = Mock()
        mock_task = Mock()
        mock_setup.return_value.__enter__ = Mock(
            return_value=(mock_ui, mock_progress, mock_task)
        )
        mock_setup.return_value.__exit__ = Mock(return_value=False)

        mock_prepare.return_value = ResumeContext(
            lines={1: "line 1"},
            job_text="job text",
        )
        mock_generate.return_value = None  # generation failed

        ctx = TailoringContext(
            settings=mock_settings,
            resume=Path("resume.docx"),
            job=Path("job.txt"),
            model="gpt-4o",
            edits_json=Path("edits.json"),
        )
        runner = TailoringRunner(TailoringMode.GENERATE, ctx)

        with pytest.raises(EditError, match="Failed to generate valid edits"):
            runner.run()
