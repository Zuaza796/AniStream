"""AnimeAv1 provider adapted from anicli-esp 1.3.1 (MIT); see third_party/anicli-esp/."""
import re
import base64
import codecs
import json
import logging
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urljoin, urlparse
from bs4 import BeautifulSoup

BASE = 'https://animeav1.com'

def fetch(url, referer=None):
    if urlparse(url).scheme != 'https':
        raise ValueError('Enlace de reproducción no seguro')
    headers = {'User-Agent': 'Mozilla/5.0'}
    if referer: headers['Referer'] = referer
    for attempt in range(2):
        try:
            with urlopen(Request(url, headers=headers), timeout=12) as r:
                return r.read()
        except HTTPError as e:
            if e.code not in (408, 429, 500, 502, 503, 504) or attempt: raise
        except (URLError, TimeoutError, OSError):
            if attempt: raise
        time.sleep(0.4)


def catalog(query=''):
    soup = BeautifulSoup(fetch(BASE + '/catalogo?' + urlencode({'search': query})), 'html.parser')
    items = []
    for article in soup.select('article'):
        a, title, img = article.select_one('a[href^="/media/"]'), article.select_one('h3'), article.select_one('img')
        if a and title:
            items.append(dict(title=title.get_text(' ', strip=True), path=a['href'], image=urljoin(BASE, img['src']) if img else '', description=article.select_one('p').get_text(' ', strip=True) if article.select_one('p') else ''))
    return items

def episodes(item):
    text = fetch(BASE + item['path']).decode()
    data = re.search(r'episodes:\[(.*?)\]', text, re.S)
    nums = re.findall(r'number:(\d+)', data[1]) if data else []
    if not nums:
        soup = BeautifulSoup(text, 'html.parser')
        nums = [a['href'].rsplit('/', 1)[-1] for a in soup.select('article a[href]') if a['href'].startswith(item['path'] + '/') and a['href'].rsplit('/', 1)[-1].isdigit()]
    result = sorted(set(map(int, nums)))
    if not result:
        raise RuntimeError('El proveedor no devolvió episodios para esta serie.')
    return result

def sources(item, episode):
    text = fetch(BASE + item['path'] + '/' + str(episode)).decode()
    embeds = re.search(r'embeds:\{(.*?)\},downloads:', text, re.S)
    if not embeds:
        raise RuntimeError('El proveedor no devolvió servidores para este episodio.')
    # Limit parsing to embeds; download links are not playback sources.
    pairs = re.findall(r'server:"([^"]+)",url:"([^"]+)"', embeds[1])
    result = []
    for name in ('MP4Upload', 'Voe'):
        for server, url in pairs:
            if server == name:
                candidate = dict(name=server, embed=url.replace('\\', ''))
                if candidate not in result: result.append(candidate)
    if not result:
        raise RuntimeError('Este episodio no tiene un servidor compatible disponible.')
    return result


def check_media(url, referer):
    """Check a small byte range, including the first HLS segment, before playback."""
    for _ in range(4):
        if urlparse(url).scheme != 'https': raise RuntimeError('URL de vídeo incompatible')
        req = Request(url, headers={'User-Agent':'Mozilla/5.0', 'Referer':referer, 'Range':'bytes=0-16383'})
        with urlopen(req, timeout=10) as response:
            data = response.read(16384)
        if not data: raise RuntimeError('El servidor devolvió un vídeo vacío')
        if not data.startswith(b'#EXTM3U'): return
        lines = data.decode().splitlines()
        next_url = next((line.strip() for line in lines if line.strip() and not line.startswith('#')), None)
        if not next_url: raise RuntimeError('Lista de reproducción vacía')
        url = urljoin(url, next_url)
    raise RuntimeError('No se pudo comprobar el vídeo HLS')


def resolve(source):
    name, embed = source['name'], source['embed']
    logging.info('Resolving server=%s host=%s', name, urlparse(embed).hostname)
    page = fetch(embed, BASE + '/').decode()
    if name == 'MP4Upload':
        match = re.search(r'src:\s*[\"\'](https:[^\"\']+)[\"\']', page)
        if not match:
            raise RuntimeError('MP4Upload no devolvió un enlace de vídeo.')
        url = match[1].replace('\\', '')
        if not re.search(r'\.(mp4|m3u8)(?:[?]|$)', url):
            raise RuntimeError('MP4Upload devolvió una respuesta sin vídeo.')
        check_media(url, 'https://www.mp4upload.com/')
        return dict(url=url, referer='https://www.mp4upload.com/', server=name)
    if name == 'Voe':
        # The host uses a JS redirect. Read the literal destination without executing JS.
        for _ in range(3):
            target = re.search(r'window\.location\.href\s*=\s*[\"\'](https://[^\"\']+)', page)
            if not target: break
            embed = target[1]
            page = fetch(embed, BASE + '/').decode()
        soup = BeautifulSoup(page, 'html.parser')
        script = soup.select_one('script[type="application/json"]')
        if not script:
            raise RuntimeError('Voe no devolvió los datos del vídeo.')
        # Decode the player's data-only encoding. No site scripts are evaluated.
        encoded = json.loads(script.string)[0]
        encoded = re.sub(r'[^A-Za-z0-9+/=]', '', codecs.decode(encoded, 'rot_13'))
        shifted = base64.b64decode(encoded).decode()
        encoded = ''.join(chr(ord(c) - 3) for c in shifted)[::-1]
        payload = json.loads(base64.b64decode(encoded))
        url = payload.get('source')
        if not url or urlparse(url).scheme != 'https':
            raise RuntimeError('Voe no devolvió un enlace de vídeo válido.')
        check_media(url, embed)
        return dict(url=url, referer=embed, server=name)
    raise RuntimeError('Servidor incompatible: ' + name)


def stream(item, episode):
    errors = []
    for source in sources(item, episode):
        try: return resolve(source)['url']
        except Exception as e: errors.append(str(e))
    raise RuntimeError('No se pudo obtener el vídeo. ' + ' · '.join(errors))
