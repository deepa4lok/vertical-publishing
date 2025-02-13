from odoo.tests.common import Form
from .common import CommonSaleAdvertisingOrder


class TestSaleAdvertisingOrderOnchange(CommonSaleAdvertisingOrder):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.multi_issues = cls.env['sale.advertising.issue']
        for i in range(10):
            cls.multi_issues += cls.issue2.copy({'analytic_account_id': cls.issue2.analytic_account_id.id})
        cls.product_template_digital2.list_price = 395

    def test_rounding(self):
        with Form(self.order, self.order_view) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.medium = self.product_category_main
                line_form.title_ids.add(self.title2)
                for issue in self.multi_issues:
                    line_form.adv_issue_ids.add(issue)
                line_form.product_template_id = self.product_template_digital2
                line_form.subtotal_before_agency_disc = 800
                line_form.discount_reason_id = self.discount_reason

        self.env['sale.order.line.create.multi.lines'].with_context(
            active_model=self.order._name, active_id=self.order.id, active_ids=self.order.ids,
        ).create_multi_lines(raise_exception=False)

        self.assertEqual(len(self.order.order_line), 10)
        for line in self.order.order_line:
            self.assertEqual(line.subtotal_before_agency_disc, 80)
            self.assertEqual(line.actual_unit_price, 80)
            self.assertEqual(round(line.computed_discount, 2), 79.75)
