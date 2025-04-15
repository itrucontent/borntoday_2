from django.http import HttpResponse
from django.views.decorators.http import require_GET
import os


@require_GET
def robots_txt(request):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    robots_file = os.path.join(BASE_DIR, 'static', 'robots.txt')

    try:
        with open(robots_file, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type="text/plain")
    except FileNotFoundError:
        return HttpResponse("User-agent: *\nDisallow: /", content_type="text/plain")