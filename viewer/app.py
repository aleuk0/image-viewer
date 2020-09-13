from dataclasses import dataclass
from typing import Dict, List
import json
import csv
import sys
import os

from aiohttp import web
import aiohttp_jinja2
import jinja2


sys.path.append(".")


@dataclass
class Image:
    url: str
    needed_amount_of_shows: int
    categories: List[str]

    def count(self):
        return self.needed_amount_of_shows


@aiohttp_jinja2.template("index.html")
def get_photo(request: web.Request) -> Dict:
    images = request.app['images']
    last_used_url = request.app['last_shown_img_url']
    result_image = None

    categories = []
    if request.query_string:
        categories = [
            category.split('=')[1] for category in request.query_string.split('&')
        ]
    else:
        result_image = images[0]

    reserve = None  # для уменьшения вероятности выдачи одной и той же картинки
    if not result_image:
        for img in images:
            common_cat = len(set(img.categories) & set(categories))
            if common_cat:
                if img.url == last_used_url:
                    reserve = img
                    continue
                result_image = img
                break

    if not result_image and reserve:
        result_image = reserve

    if not result_image:
        return

    result_image.needed_amount_of_shows -= 1
    if result_image.needed_amount_of_shows < 1:
        images.remove(result_image)

    request.app['last_shown_img_url'] = result_image.url
    request.app['images'] = sorted(images, key=Image.count, reverse=True)

    return {
        'result_image': result_image,
    }


async def init_app() -> web.Application:
    app = web.Application()
    aiohttp_jinja2.setup(
        app, loader=jinja2.PackageLoader('viewer', 'templates'))

    images = []
    with open('./config.csv', newline='') as f:
        images_csv = csv.reader(f, delimiter=';')
        for row in images_csv:
            csv_image_categories = [cat for cat in row[2:]]
            if int(row[1]) > 0:
                images.append(Image(row[0], int(row[1]), csv_image_categories))
    app['images'] = sorted(images, key=Image.count, reverse=True)

    app['last_shown_img_url'] = None

    routes = [
        web.static(
            '/static', os.path.join(os.path.dirname(__file__), 'static'),
        ),
        web.get('/', get_photo),
    ]
    app.add_routes(routes)

    return app


def main():
    web.run_app(init_app())


if __name__ == '__main__':
    main()
