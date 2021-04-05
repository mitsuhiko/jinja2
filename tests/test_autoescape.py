class TestCustomAutoescape:
    def test_custom_join(self, env_custom_autoescape):
        from jinja2.nodes import EvalContext

        ctx = EvalContext(env_custom_autoescape)
        escape = ctx.get_escape_function()
        combine = ["$foo", escape("$bar"), ctx.mark_safe("$dollar")]
        assert ctx.mark_safe("").join(combine) == "€foo€bar$dollar"

    def test_non_custom_modulo(self, env):
        from jinja2.nodes import EvalContext

        ctx = EvalContext(env)
        escape = ctx.get_escape_function()
        source = ctx.mark_safe("%s,%s,%s")
        target = ("$foo", escape("$bar"), ctx.mark_safe("$dollar"))
        assert source % target == "$foo,$bar,$dollar"

    def test_custom_modulo(self, env_custom_autoescape):
        from jinja2.nodes import EvalContext

        ctx = EvalContext(env_custom_autoescape)
        escape = ctx.get_escape_function()
        source = ctx.mark_safe("%s,%s,%s")
        target = ("$foo", escape("$bar"), ctx.mark_safe("$dollar"))
        assert source % target == "€foo,€bar,$dollar"
