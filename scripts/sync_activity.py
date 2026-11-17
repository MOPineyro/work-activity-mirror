#!/usr/bin/env python3
"""Append disclosed activity markers from a public GitHub contribution calendar."""
import argparse
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'activity.json'


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.tooltips = {}
        self.target = None
        self.text = []
        self.in_heading = False
        self.heading = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'td' and attrs.get('data-date') and attrs.get('id'):
            day = date.fromisoformat(attrs['data-date']).isoformat()
            self.cells[attrs['id']] = day
        if tag == 'tool-tip':
            self.target = attrs.get('for')
            self.text = []
        if tag == 'h2' and attrs.get('id') == 'js-contribution-activity-description':
            self.in_heading = True

    def handle_data(self, data):
        if self.target:
            self.text.append(data)
        if self.in_heading:
            self.heading.append(data)

    def handle_endtag(self, tag):
        if tag == 'tool-tip' and self.target:
            self.tooltips[self.target] = ''.join(self.text).strip()
            self.target = None
        if tag == 'h2':
            self.in_heading = False

    def counts(self):
        days = {}
        for cell, day in self.cells.items():
            text = self.tooltips.get(cell, '')
            match = re.match(r'^(No|[\d,]+) contributions?\b', text)
            if not match:
                raise ValueError(f'Unrecognized contribution tooltip for {day}: {text!r}')
            days[day] = 0 if match[1] == 'No' else int(match[1].replace(',', ''))
        heading = ' '.join(''.join(self.heading).split())
        total = re.search(r'([\d,]+) contributions? in the last year', heading)
        if not total or len(days) < 350:
            raise ValueError('A complete public contribution calendar was not returned')
        if sum(days.values()) != int(total[1].replace(',', '')):
            raise ValueError('Daily contribution counts differ from the calendar heading')
        return days


def git(*args, env=None):
    return subprocess.run(['git', '-C', str(ROOT), *args], env=env,
                          check=True, capture_output=True, text=True).stdout.strip()


def pending(source, recorded):
    decreases = {day: (recorded.get(day, 0), count) for day, count in source.items()
                 if recorded.get(day, 0) > count}
    if decreases:
        raise ValueError(f'Source counts decreased; review before changing history: {decreases}')
    return [(day, recorded.get(day, 0) + 1, count)
            for day, count in sorted(source.items()) if count > recorded.get(day, 0)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--push', action='store_true', help='Publish at most 500 new markers per push')
    args = parser.parse_args()
    state = json.loads(STATE.read_text())
    account = state['source_account']
    if not re.fullmatch(r'[A-Za-z0-9-]+', account):
        raise ValueError('Invalid source account')
    url = f'https://github.com/users/{account}/contributions'
    request = urllib.request.Request(url, headers={'User-Agent': 'work-activity-mirror',
                                                 'Accept-Language': 'en-US,en;q=0.9'})
    with urllib.request.urlopen(request, timeout=60) as response:
        html = response.read().decode('utf-8')
    calendar = CalendarParser()
    calendar.feed(html)
    source = calendar.counts()
    changes = pending(source, state['days'])
    count = sum(end - start + 1 for _, start, end in changes)
    print(f'Source: {sum(source.values())} contributions; pending markers: {count}', flush=True)
    if args.dry_run or not count:
        return
    if git('status', '--porcelain'):
        raise RuntimeError('Commit or discard local changes before syncing')
    email = git('config', '--get', 'user.email')
    if not email.endswith('@users.noreply.github.com'):
        raise RuntimeError('Configure a GitHub noreply author email before syncing')
    state['schema_version'] = 1
    state['scope'] = 'Daily counts from the full public GitHub contribution calendar'
    state['source_url'] = url
    state['date_basis'] = 'Dates displayed on the public contribution calendar'
    state.pop('utc_fallback_commits', None)
    done = 0
    for day, start, end in changes:
        for ordinal in range(start, end + 1):
            state['days'][day] = ordinal
            state['days'] = dict(sorted(state['days'].items()))
            state['total_markers'] = sum(state['days'].values())
            state['active_days'] = len(state['days'])
            state['last_synced_at'] = datetime.now(timezone.utc).isoformat()
            STATE.write_text(json.dumps(state, indent=2) + '\n')
            git('add', 'activity.json')
            stamp = (datetime.fromisoformat(f'{day}T12:00:00+00:00')
                     + timedelta(seconds=ordinal - 1)).isoformat()
            env = os.environ.copy()
            env.update(GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
            git('commit', '-m', f'Mirror public work activity for {day} ({ordinal}/{end})', env=env)
            done += 1
            if args.push and done % 500 == 0:
                git('push', 'origin', 'HEAD:main')
            if done % 250 == 0:
                print(f'Created {done}/{count} new markers', flush=True)
    if args.push and done % 500:
        git('push', 'origin', 'HEAD:main')
    assert not pending(source, state['days'])
    print(f'Imported {done} markers; stored total: {state["total_markers"]}', flush=True)


if __name__ == '__main__':
    main()
