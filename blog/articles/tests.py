from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Article,
    Enterprise,
    ExchangeRate,
    FinancialIndicator,
    IndicatorValue,
    ReportPeriod,
)


class ArticleDetailAndArchiveTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username="analyst24", password="test-password-93"
        )
        self.article = Article.objects.create(
            title="Динамика выручки предприятия",
            author=self.author,
            text=(
                "В отчётном периоде выручка предприятия выросла. "
                "Аналитики сравнили показатели за два периода и оценили их "
                "влияние на финансовый результат холдинга."
            ),
        )

    def test_archive_lists_article_and_links_title_to_detail(self):
        response = self.client.get(reverse("archive"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)
        self.assertContains(response, "analyst24")
        self.assertContains(response, reverse("get_article", args=[self.article.id]))

    def test_article_detail_displays_full_article_and_back_link(self):
        response = self.client.get(reverse("get_article", args=[self.article.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)
        self.assertContains(response, self.article.text)
        self.assertContains(response, "Все записи")
        self.assertContains(response, "analyst24")

    def test_unknown_article_returns_404(self):
        response = self.client.get(reverse("get_article", args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_non_numeric_article_id_does_not_match_detail_route(self):
        response = self.client.get("/article/not-a-number/")
        self.assertEqual(response.status_code, 404)

    def test_excerpt_is_limited_to_140_characters_plus_ellipsis(self):
        self.article.text = "x" * 150
        self.assertEqual(self.article.get_excerpt(), "x" * 140 + "...")
        self.article.text = "short text"
        self.assertEqual(self.article.get_excerpt(), "short text")


class FinancialDashboardTests(TestCase):
    def test_financial_dashboard_renders_enterprises_indicators_and_rates(self):
        enterprise = Enterprise.objects.create(
            name="Учебное предприятие Альфа",
            requisites="DEMO-001",
            phone="+7 000 000-00-01",
            contact_person="Иван Иванов",
        )
        period = ReportPeriod.objects.create(
            title="I квартал 2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        indicator = FinancialIndicator.objects.create(
            name="Выручка",
            importance=Decimal("1.000"),
            unit="money",
            currency="RUB",
        )
        IndicatorValue.objects.create(
            enterprise=enterprise,
            report_period=period,
            indicator=indicator,
            value=Decimal("1500000.00"),
        )
        ExchangeRate.objects.create(
            base_currency="USD",
            quote_currency="RUB",
            rate=Decimal("90.000000"),
            effective_date=date(2026, 3, 31),
        )
        response = self.client.get(reverse("financial-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Учебное предприятие Альфа")
        self.assertContains(response, "1500000")
        self.assertContains(response, "USD")



class CreatePostTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="financial_writer", password="test-password-93"
        )
        self.existing_article = Article.objects.create(
            title="Уникальный отчёт о выручке",
            author=self.user,
            text="Текст ранее опубликованной аналитической статьи.",
        )

    def test_anonymous_user_cannot_open_create_form(self):
        response = self.client.get(reverse("create_post"))
        self.assertEqual(response.status_code, 404)

    def test_authenticated_user_can_open_form(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("create_post"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "create_post.html")
        self.assertContains(response, "Сохранить статью")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_valid_post_creates_article_for_current_user_and_redirects(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("create_post"),
            {"title": "Прибыль за второй квартал", "text": "Прибыль увеличилась."},
        )
        article = Article.objects.get(title="Прибыль за второй квартал")
        self.assertEqual(article.author, self.user)
        self.assertEqual(article.text, "Прибыль увеличилась.")
        self.assertRedirects(response, reverse("get_article", args=[article.id]))

    def test_missing_text_returns_form_with_error_and_preserves_input(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("create_post"),
            {"title": "Черновик без текста", "text": "   "},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Проверьте обязательные поля")
        self.assertContains(response, "Введите текст статьи.")
        self.assertNotContains(response, "Введите название статьи.")
        self.assertContains(response, "Черновик без текста")
        self.assertEqual(Article.objects.count(), 1)

    def test_both_empty_fields_show_individual_errors(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("create_post"), {"title": "   ", "text": "   "}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите название статьи.")
        self.assertContains(response, "Введите текст статьи.")
        self.assertContains(response, 'aria-invalid="true"', count=2)
        self.assertEqual(Article.objects.count(), 1)

    def test_missing_title_shows_error_next_to_title_field(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("create_post"),
            {"title": "   ", "text": "Текст финансовой аналитической статьи."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите название статьи.")
        self.assertNotContains(response, "Введите текст статьи.")
        self.assertEqual(Article.objects.count(), 1)

    def test_missing_text_shows_error_next_to_text_field(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("create_post"),
            {"title": "Черновик без текста", "text": "   "},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите текст статьи.")
        self.assertNotContains(response, "Введите название статьи.")
        self.assertEqual(Article.objects.count(), 1)

    def test_duplicate_title_is_rejected_case_insensitively(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("create_post"),
            {"title": "уникальный отчёт о ВЫРУЧКЕ", "text": "Другой текст."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Статья с таким названием уже существует")
        self.assertEqual(Article.objects.count(), 1)
