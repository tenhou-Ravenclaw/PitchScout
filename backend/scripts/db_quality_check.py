"""songs.db のデータ品質チェックスクリプト"""
import sqlite3
import re
import csv
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'songs.db')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Artists with missing reading
print('=== 1. Artists with NULL/empty reading ===')
cur.execute("SELECT id, name, slug, reading FROM artists WHERE reading IS NULL OR reading = ''")
missing_reading = cur.fetchall()
if missing_reading:
    for r in missing_reading:
        print(f"  id={r['id']}, name={r['name']}, slug={r['slug']}, reading={r['reading']}")
else:
    print('  None - all artists have readings')

# 2. Total counts
print('\n=== 2. Basic counts ===')
cur.execute('SELECT COUNT(*) as c FROM artists')
artist_count = cur.fetchone()['c']
print(f'  Artists: {artist_count}')
cur.execute('SELECT COUNT(*) as c FROM songs')
song_count = cur.fetchone()['c']
print(f'  Songs: {song_count}')

# 3. Songs with missing notes
print('\n=== 3. Songs with NULL/empty notes ===')
cur.execute("SELECT COUNT(*) as c FROM songs WHERE lowest_note IS NULL OR lowest_note = ''")
print(f"  Missing lowest_note: {cur.fetchone()['c']}")
cur.execute("SELECT COUNT(*) as c FROM songs WHERE highest_note IS NULL OR highest_note = ''")
print(f"  Missing highest_note: {cur.fetchone()['c']}")
cur.execute("SELECT COUNT(*) as c FROM songs WHERE falsetto_note IS NULL OR falsetto_note = ''")
print(f"  Missing falsetto_note: {cur.fetchone()['c']}")

# 4. Orphan songs
print('\n=== 4. Orphan songs (artist_id not in artists) ===')
cur.execute('SELECT COUNT(*) as c FROM songs WHERE artist_id NOT IN (SELECT id FROM artists)')
print(f"  Orphan songs: {cur.fetchone()['c']}")

# 5. song_count accuracy
print('\n=== 5. song_count mismatches ===')
cur.execute('''
    SELECT a.id, a.name, a.song_count, COUNT(s.id) as actual_count
    FROM artists a LEFT JOIN songs s ON a.id = s.artist_id
    GROUP BY a.id
    HAVING a.song_count != COUNT(s.id)
''')
mismatches = cur.fetchall()
print(f'  Total mismatches: {len(mismatches)}')
for r in mismatches[:20]:
    print(f"  id={r['id']}, name={r['name']}, recorded={r['song_count']}, actual={r['actual_count']}")

# 6. Cross-source duplicates
print('\n=== 6. Cross-source duplicates ===')
cur.execute('''
    SELECT COUNT(*) as c FROM (
        SELECT artist_id, title FROM songs
        GROUP BY artist_id, title
        HAVING COUNT(DISTINCT source) > 1
    )
''')
dup_count = cur.fetchone()['c']
print(f'  Duplicate song pairs: {dup_count}')

if dup_count > 0:
    cur.execute('''
        SELECT s1.title, a.name as artist, s1.source as src1, s2.source as src2
        FROM songs s1
        JOIN songs s2 ON s1.artist_id = s2.artist_id AND s1.title = s2.title AND s1.source < s2.source
        JOIN artists a ON a.id = s1.artist_id
        LIMIT 10
    ''')
    print('  Examples:')
    for r in cur.fetchall():
        print(f"    {r['artist']} - {r['title']} ({r['src1']} vs {r['src2']})")

# 7. Note format validation
print('\n=== 7. Note format validation ===')
NOTE_PATTERN = re.compile(r'^(lowlow|low|mid1|mid2|hi|hihi|hihihi)[A-G]#?$')
for col in ['lowest_note', 'highest_note', 'falsetto_note']:
    cur.execute(f"SELECT DISTINCT {col} FROM songs WHERE {col} IS NOT NULL AND {col} != ''")
    all_notes = [r[0] for r in cur.fetchall()]
    invalid = [n for n in all_notes if not NOTE_PATTERN.match(n)]
    print(f'  {col}: {len(all_notes)} unique values, {len(invalid)} invalid')
    if invalid:
        print(f'    Invalid: {invalid}')

# 8. Source distribution
print('\n=== 8. Source distribution ===')
cur.execute('SELECT source, COUNT(*) as c FROM songs GROUP BY source')
for r in cur.fetchall():
    print(f"  {r['source']}: {r['c']} songs")

# 9. Export all data to CSV for visual review
print('\n=== 9. Exporting CSVs ===')

# Artists CSV
cur.execute('SELECT id, name, slug, song_count, reading FROM artists ORDER BY id')
with open(os.path.join(OUTPUT_DIR, 'artists_check.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'name', 'slug', 'song_count', 'reading'])
    writer.writerows(cur.fetchall())
print('  artists_check.csv exported')

# Songs CSV
cur.execute('''
    SELECT s.id, a.name as artist_name, s.title, s.lowest_note, s.highest_note,
           s.falsetto_note, s.note, s.source
    FROM songs s JOIN artists a ON a.id = s.artist_id
    ORDER BY a.name, s.title
''')
with open(os.path.join(OUTPUT_DIR, 'songs_check.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'artist_name', 'title', 'lowest_note', 'highest_note',
                     'falsetto_note', 'note', 'source'])
    writer.writerows(cur.fetchall())
print('  songs_check.csv exported')

# Issues CSV
cur.execute("""
    SELECT s.id, a.name as artist_name, s.title, s.lowest_note, s.highest_note,
           s.falsetto_note, s.source,
           CASE
               WHEN s.lowest_note IS NULL OR s.lowest_note = '' THEN 'missing_lowest'
               WHEN s.highest_note IS NULL OR s.highest_note = '' THEN 'missing_highest'
           END as issue
    FROM songs s JOIN artists a ON a.id = s.artist_id
    WHERE s.lowest_note IS NULL OR s.lowest_note = ''
       OR s.highest_note IS NULL OR s.highest_note = ''
    ORDER BY a.name, s.title
""")
with open(os.path.join(OUTPUT_DIR, 'songs_issues.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'artist_name', 'title', 'lowest_note', 'highest_note',
                     'falsetto_note', 'source', 'issue'])
    writer.writerows(cur.fetchall())
print('  songs_issues.csv exported')

conn.close()
print('\nDone!')
