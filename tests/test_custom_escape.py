from markupsafe import Markup

from jinja2 import Environment


class CustomMarkup(Markup):
    @classmethod
    def escape(cls, s):
        if hasattr(s, "__html__"):
            return s
        return cls(s.replace("$", "€"))


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
        assert t.render(foo="<FOO>") == "<FOO>"

    def test_custom_markup_environment_autoescape(self):
        env = Environment(default_markup_class=CustomMarkup, autoescape=True)
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

    def test_custom_markup_environment_manual_escape(self):
        env = Environment(default_markup_class=CustomMarkup)
        t = env.from_string("{{ foo|e }}")
        assert t.render(foo="100$") == "100€"
        t = env.from_string("{{ foo|escape }}")
        assert t.render(foo="100$") == "100€"
        t = env.from_string("{{ foo|safe }}")
        assert t.render(foo="100$") == "100$"
        t = env.from_string("{{ foo|safe|escape }}")
        assert t.render(foo="100$") == "100$"
