from django.http import Http404
from django.shortcuts import redirect, render

from .models import Article, Enterprise, ExchangeRate, IndicatorValue


def archive(request):
    """Show all analyst articles; each title links to its detail page."""
    posts = Article.objects.select_related("author").order_by("-created_date", "-id")
    return render(request, "archive.html", {"posts": posts})


def get_article(request, article_id):
    """Show a single article selected by its numeric database ID."""
    try:
        post = Article.objects.select_related("author").get(id=article_id)
    except Article.DoesNotExist as exc:
        raise Http404("Статья не найдена") from exc
    return render(request, "article.html", {"post": post})


def financial_dashboard(request):
    """Overview of financial indicators and exchange rates for variant 24."""
    enterprises = Enterprise.objects.all()
    values = IndicatorValue.objects.select_related(
        "enterprise", "report_period", "indicator"
    ).order_by("-report_period__start_date", "enterprise__name", "indicator__name")
    rates = ExchangeRate.objects.all().order_by("-effective_date")[:30]
    return render(
        request,
        "financial_dashboard.html",
        {"enterprises": enterprises, "indicator_values": values, "exchange_rates": rates},
    )


def create_post(request):
    """Create an article for the authenticated user."""
    if not request.user.is_authenticated:
        raise Http404

    initial_form = {"title": "", "text": ""}
    if request.method != "POST":
        return render(request, "create_post.html", {"form": initial_form})

    title = request.POST.get("title", "").strip()
    text = request.POST.get("text", "").strip()
    form = {"title": title, "text": text}

    if not title or not text:
        form["errors"] = "Заполните название и текст статьи."
        return render(request, "create_post.html", {"form": form})

    # SQLite's built-in case-insensitive comparison does not reliably handle
    # Cyrillic characters. Compare casefolded titles in Python instead.
    normalized_title = title.casefold()
    existing_titles = Article.objects.values_list("title", flat=True)
    title_exists = any(
        existing_title.casefold() == normalized_title
        for existing_title in existing_titles
    )
    if title_exists:
        form["errors"] = (
            "Статья с таким названием уже существует. Выберите другое название."
        )
        return render(request, "create_post.html", {"form": form})

    post = Article.objects.create(
        title=title,
        text=text,
        author=request.user,
    )
    return redirect("get_article", article_id=post.id)
