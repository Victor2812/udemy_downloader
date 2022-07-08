import argparse
import os
import requests
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


__author__ = "github.com/6e0d0a"
__version__ = "0.1.0"


class InvalidTokenException(Exception):
    pass


class ResourceNotFound(Exception):
    pass


class UdemyAPI:
    API_URL = "https://www.udemy.com/api-2.0/"
    PAGE_SIZE = 100

    def __init__(self, token) -> None:
        self._s = requests.session()
        self._s.cookies.set('access_token', token)

    def __get(self, path: str, params: Dict = {}) -> requests.Response:
        params['page_size'] = self.PAGE_SIZE

        r = self._s.get(self.API_URL + path, params=params)

        if r.status_code == 403:
            raise InvalidTokenException("Access denied")
        elif r.status_code == 404:
            raise ResourceNotFound(r.json()['detail'])
        elif r.status_code == 200:
            return r
        else:
            raise Exception(f"Unhandled status code: {r.status_code}")

    def get_my_courses(self) -> Tuple[int, Dict]:
        """Gets the courses the user is subscribed to"""
        data = self.__get("users/me/subscribed-courses").json()
        return data['count'], data['results']

    def get_course_lectures(self, course_id: int) -> Tuple[int, Dict]:
        """Obtains course readings"""
        data = self.__get(f"courses/{course_id}/cached-subscriber-curriculum-items/").json()
        return data['count'], data['results']

    def get_course_lecture_data(self, course_id: int, lecture_id: int):
        """Obtains information from a lesson"""
        data = self.__get(f"users/me/subscribed-courses/{course_id}/lectures/{lecture_id}", {
            "fields[lecture]": "asset,supplementary_assets",
            "fields[asset]": "asset_type,download_urls,captions,title,filename,data,body,media_sources"
        }).json()
        return data



def get_course_download_data(api: UdemyAPI, course: Dict) -> List:
    title = course['title']
    
    logging.info(f'Getting information of "{title}"...')
    l_count, lectures = api.get_course_lectures(course['id'])
    logging.info(f'{l_count} lessons found for "{title}"')

    chapter = ''
    chapter_index = 0
    element_index = 1
    download_queue = []

    for i, lecture in enumerate(lectures):
        logging.info(f"Getting lesson information... {(i+1) / l_count * 100:0.1f}%")

        if lecture['_class'].lower() == 'chapter':
            chapter = lecture['title']
            chapter_index += 1
        else:
            lecture = api.get_course_lecture_data(course['id'], lecture['id'])
            asset = lecture['asset']
            supplementary_assets = lecture['supplementary_assets']

            if asset['asset_type'].lower() == 'video':
                download_queue.append({
                    'chapter': chapter,
                    'chapter_index': chapter_index,
                    'element_index': element_index,
                    't': 'file',
                    'dst': asset['filename'],
                    'src': asset['media_sources'][0]['src']
                })

                for c in asset['captions']:
                    download_queue.append({
                        'chapter': chapter,
                        'chapter_index': chapter_index,
                        'element_index': element_index,
                        't': 'caption',
                        'ext': 'vtt',
                        'src': c['url'],
                        'locale': c['locale_id'],
                        'parent': asset['filename']
                    })
                element_index += 1

            elif asset['asset_type'].lower() == 'article':
                download_queue.append({
                    'chapter': chapter,
                    'chapter_index': chapter_index,
                    'element_index': element_index,
                    't': 'article',
                    'title': asset['title'],
                    'html': asset['body']
                })
                element_index += 1

            for sa in supplementary_assets:
                download_queue.append({
                    'chapter': chapter,
                    'chapter_index': chapter_index,
                    'element_index': element_index - 1, # -1 porque generalmente se refieren al elemento anterior
                    't': 'file',
                    'dst': sa['filename'],
                    'src': sa['download_urls']['File'][0]['file']
                })

    return download_queue


def download_file(src: str, dst: str):
    with open(dst, 'wb') as f:
        r = requests.get(src, stream=True)
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)


def downloader(course_name: str, element: Dict):
    if element['t'] == 'file':
        logging.info(f'Downloading "{element["dst"]}"...')

        name = element['dst']

        if element['element_index'] > 0:
            name = f"{element['element_index']}. {name}"

        path = course_name

        if element['chapter']:
            path = os.path.join(path, f"{element['chapter_index']}. {element['chapter']}")

        try:
            os.makedirs(path)
        except FileExistsError:
            pass

        path = os.path.join(path, name)

        if os.path.isfile(path):
            logging.warning(f'Excluyendo "{path}" (ya existe)')
        else:
            download_file(element['src'], path)
        logging.info(f'File "{element["dst"]}" downloaded')

    elif element['t'] == 'caption':
        name = os.path.basename(element['parent']).rpartition('.')[0]
        element['dst'] = f"{name}.{element['locale']}.{element['ext']}"
        element['t'] = 'file'
        downloader(course_name, element)
    elif element['t'] == 'article':
        logging.info(f'Getting article "{element["title"]}"')


def word_course_selector(courses: List[Dict], words: List[str]) -> Dict|None:
    for c in courses:
        if all(map(lambda x: x in c['title'].lower(), words)):
            return c


def manual_course_selector(courses: List[Dict]) -> Dict:
    print("Available courses:")
    for i, c in enumerate(courses):
        print(f' {i}.-', c['title'])
    while True:
        try:
            return courses[int(input("Course number: "))]
        except (ValueError, IndexError):
            pass


def main():
    parser = argparse.ArgumentParser(description="Udemy Course Downloader")
    parser.add_argument('-d', '--debug', help="Enable debug output", action='store_true')
    parser.add_argument('-w', '--words', help="Keywords to search for the course to download")
    parser.add_argument('token', help='Udemy "access_token" cookie')

    args = parser.parse_args()
    
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    

    logging.info(f'Getting courses...')
    api = UdemyAPI(args.token)
    courses_count, courses = api.get_my_courses()

    selected_course = None # Curso seleccionado

    if courses_count < 1:
        logging.warning("The user has not subscribed to any course.")
        exit(1)
    else:
        # Seleccionar el curso que será descargado
        if args.words:
            words = [w for w in args.words.split(' ') if w]
            selected_course = word_course_selector(courses, words)
        else:
            selected_course = manual_course_selector(courses)

    if not selected_course:
        logging.warning("No course could be selected")
    else:
        elements = get_course_download_data(api, selected_course)           

        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            for e in elements:
                futures.append(executor.submit(downloader, selected_course['title'], e))
            for f in as_completed(futures):
                f.result()


if __name__ == "__main__":
    main()