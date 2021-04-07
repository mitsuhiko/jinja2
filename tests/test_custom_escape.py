import pytest

from jinja2 import DictLoader
from jinja2 import Environment
from jinja2 import select_autoescape
from jinja2.utils import get_wrapped_escape_class


def custom_escape(s):
    return str(s).replace("$", "€")


class TestCustomAutoescape:
    def test_custom_join(self, env_custom_autoescape):
        from jinja2.nodes import EvalContext

        ctx = EvalContext(env_custom_autoescape)
        escape = ctx.get_escape_function()
        combine = ["$foo", escape("$bar"), ctx.mark_safe("$dollar")]
        assert ctx.mark_safe("").join(combine) == "€foo€bar$dollar"
        # Make sure the result was really marked as escaped
        assert escape(ctx.mark_safe("").join(combine)) == "€foo€bar$dollar"

    def test_non_custom_modulo(self, env):
        from jinja2.nodes import EvalContext

        ctx = EvalContext(env)
        escape = ctx.get_escape_function()
        source = ctx.mark_safe("%s,%s,%s")
        target = ("$foo", escape("$bar"), ctx.mark_safe("$dollar"))
        assert source % target == "$foo,$bar,$dollar"
        # Make sure the result was marked as escaped
        assert escape(source % target) == "$foo,$bar,$dollar"

    def test_eval_contex(self, env_custom_autoescape):
        t = env_custom_autoescape.from_string(
            "{% autoescape true %}|{{ foo }}|{% endautoescape %}"
        )
        assert t.render(foo="bar$>") == "|bar€>|"
        t = env_custom_autoescape.from_string(
            "{% autoescape false %}|{{ foo }}|{% endautoescape %}"
        )
        assert t.render(foo="bar$>") == "|bar$>|"

    def test_custom_modulo(self, env_custom_autoescape):
        from jinja2.nodes import EvalContext

        ctx = EvalContext(env_custom_autoescape)
        escape = ctx.get_escape_function()
        source = ctx.mark_safe("%s,%s,%s")
        target = ("$foo", escape("$bar"), ctx.mark_safe("$dollar"))
        assert source % target == "€foo,€bar,$dollar"
        # Make sure the result is marked as escaped
        assert escape(source % target) == "€foo,€bar,$dollar"

    def test_default_escape(self):
        env = Environment(autoescape=True)
        t = env.from_string("{{ foo|safe }}")
        assert t.render(foo="<$FOO$>") == "<$FOO$>"

    def test_default_escape_custom(self, env_custom_autoescape):
        env = env_custom_autoescape
        t = env.from_string("{{ foo|safe }}")
        assert t.render(foo="<$FOO$>") == "<$FOO$>"

    @pytest.mark.parametrize(
        "escaper", [custom_escape, get_wrapped_escape_class(custom_escape)]
    )
    def test_custom_markup_environment_autoescape(self, escaper):
        env = Environment(default_escape=escaper, autoescape=True)
        t = env.from_string("{{ foo }}")
        assert t.render(foo="100$") == "100€"
        t = env.from_string("{{ foo|e }}")
        assert t.render(foo="100$") == "100€"
        t = env.from_string("{{ foo|escape }}")
        assert t.render(foo="100$") == "100€"
        t = env.from_string("{{ foo|safe }}")
        assert t.render(foo="100$") == "100$"
        t = env.from_string("{{ foo|safe|escape }}")
        assert t.render(foo="100$") == "100$"

    @pytest.mark.parametrize(
        "escaper", [custom_escape, get_wrapped_escape_class(custom_escape)]
    )
    def test_custom_markup_environment_manual_escape(self, escaper):
        env = Environment(default_escape=escaper)
        t = env.from_string("{{ foo|e }}")
        assert t.render(foo="100$") == "100€"
        t = env.from_string("{{ foo|escape }}")
        assert t.render(foo="100$") == "100€"
        t = env.from_string("{{ foo|safe }}")
        assert t.render(foo="100$") == "100$"
        t = env.from_string("{{ foo|safe|escape }}")
        assert t.render(foo="100$") == "100$"

    def test_mixed_files_include(self):
        def star(s):
            return str(s).replace("*", "star")

        def tilde(s):
            return str(s).replace("~", "tilde")

        def plus(s):
            return str(s).replace("+", "plus")

        chars = "<*~+>"

        env = Environment(
            autoescape=select_autoescape(
                special_extensions={"star": star, "tilde": tilde, "plus": plus}
            ),
            loader=DictLoader(
                {
                    "main.star": "{{ foo }};{% include 'inc.tilde' %};",
                    "inc.tilde": "{{ foo }};{% include 'simple.plus' %};",
                    "simple.plus": "{{ foo }}",
                    "simple.star": "{{ foo }}",
                    "simple.tilde": "{{ foo }}",
                }
            ),
        )
        # First test simple stuff
        t = env.get_template("simple.plus")
        assert t.render(foo=chars) == "<*~plus>"
        t = env.get_template("simple.star")
        assert t.render(foo=chars) == "<star~+>"
        t = env.get_template("simple.tilde")
        assert t.render(foo=chars) == "<*tilde+>"
        t = env.get_template("inc.tilde")
        assert t.render(foo=chars) == "<*tilde+>;<*~plus>;"
        t = env.get_template("main.star")
        assert t.render(foo=chars) == "<star~+>;<*tilde+>;<*~plus>;;"
