"""
Management command to sync GitHub public activity into public entries.
User Story #5: As an author, I want my (new, public) GitHub activity to be
automatically turned into public entries, so everyone can see my GitHub activity too.

Run: python manage.py sync_github
Or for a single author: python manage.py sync_github --author-id 1

Can be scheduled via cron for automatic periodic sync.
"""
from django.core.management.base import BaseCommand

from core.services import sync_author_github_activity, sync_all_authors_github
from core.models import Author


class Command(BaseCommand):
    help = 'Sync GitHub public activity for authors into public entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--author-id',
            type=int,
            help='Sync only this author (by ID). If omitted, syncs all authors with GitHub URL.',
        )

    def handle(self, *args, **options):
        author_id = options.get('author_id')
        if author_id:
            try:
                author = Author.objects.get(id=author_id)
            except Author.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Author {author_id} not found.'))
                return
            created, err = sync_author_github_activity(author)
            if err:
                self.stderr.write(self.style.WARNING(f'Author {author.username}: {err}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Author {author.username}: created {created} new entries.'))
        else:
            results = sync_all_authors_github()
            total = 0
            for aid, (created, err) in results.items():
                author = Author.objects.get(id=aid)
                if err:
                    self.stdout.write(f'  {author.username}: {err}')
                else:
                    self.stdout.write(f'  {author.username}: {created} new entries')
                    total += created
            self.stdout.write(self.style.SUCCESS(f'Total: {total} new entries created.'))
