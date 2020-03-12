import click
import concurrent.futures
import inmates
import magic
import urllib.request

from csv import DictReader
from hashlib import sha256
from httpx import get as GET
from pathlib import Path
from os.path import dirname

from inmates.cli import pass_environment
from inmates.utils import snapshot, hasher


@click.command('download', short_help='Downloads artifacts from links in the CSV.')
@pass_environment
def cli(ctx):
    """Extracts infromation from inmates.csv"""

    csvfile = open('inmates.csv')
    filtered = filter(lambda r: r['Roster Link'], (row for row in DictReader(csvfile)))
    roster_links = ({'county': row['IL County'], 'link': row['Roster Link']} for row in filtered)
    artifact_directory = 'commissary'

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        call = {executor.submit(GET, rl['link'], timeout=10): rl for rl in roster_links}
        for future in concurrent.futures.as_completed(call):
            rl = call[future]
            try:
                response = future.result()
            except Exception as exc:
                ctx.error(f'generated an exception: {exc}')
            else:
                if response.status_code == 200:
                    ctx.log(f'{rl}')
                    filetype = magic.from_buffer(response.content[:2048])
                    filetype_extension = filetype.split(' ')[0].lower()
                    roster_artifact = rl['county'].rstrip('County').strip().lower().replace('. ', '-')
                    with open(f'{artifact_directory}/{roster_artifact}.{filetype_extension}', 'wb') as binfile:
                        hasher.update(response.content)
                        binfile.write(response.content)

    csvfile.close()
    snapshot(artifact_directory, Path(f'{artifact_directory}/.hashfile'))

