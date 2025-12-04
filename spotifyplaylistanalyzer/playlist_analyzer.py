import spotipy
from spotipy.oauth2 import SpotifyOAuth
from urllib.parse import urlparse, parse_qs

# pls dont look at my api keys lol
CLIENT_ID = "31c4b1340fbd4acdadc7b666ebe12899"
CLIENT_SECRET = "YOUR_CLI430829129a0f42f1846fb3a328a08581"
REDIRECT_URI = "http://127.0.0.1:8888/callback"  # must match app settings
SCOPE = "playlist-read-private playlist-read-collaborative"

# Example: "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
PLAYLIST_URL = "https://open.spotify.com/playlist/0ArZDFke9Fdqrvuj1igj0Q?si=ee0b54278efc46eb"
# --


def get_playlist_id_from_url(url: str) -> str:
    """
    Extracts the playlist ID from a Spotify playlist URL.
    Works for URLs like:
    - https://open.spotify.com/playlist/PLAYLIST_ID?si=...
    - spotify:playlist:PLAYLIST_ID
    """
    if url.startswith("spotify:playlist:"):
        return url.split(":")[-1]

    parsed = urlparse(url)
    if "open.spotify.com" in parsed.netloc:
        # path looks like /playlist/PLAYLIST_ID
        parts = parsed.path.split("/")
        for i, part in enumerate(parts):
            if part == "playlist" and i + 1 < len(parts):
                return parts[i + 1]

    raise ValueError("Could not extract playlist ID from URL.")


def create_spotify_client():
    """Create an authenticated Spotipy client using OAuth."""
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
        )
    )
    return sp


def get_playlist_tracks(sp, playlist_id: str):
    """Fetch all tracks from a playlist (handles pagination)."""
    tracks = []
    results = sp.playlist_items(playlist_id, additional_types=["track"])
    while results:
        for item in results["items"]:
            track = item.get("track")
            if track and track.get("id"):
                tracks.append(track)
        # check if there's a next page
        if results["next"]:
            results = sp.next(results)
        else:
            break
    return tracks


def analyze_playlist(tracks):
    """
    Analyze basic playlist stats without using audio_features.
    Things we calculate:
    - total tracks
    - average song length
    - average popularity
    - oldest & newest song year
    - number of explicit tracks
    - top 5 most common artists
    """
    if not tracks:
        print("No tracks found.")
        return

    total_duration_ms = 0
    total_popularity = 0
    explicit_count = 0
    years = []
    artist_counts = {}

    for t in tracks:
        # duration
        total_duration_ms += t.get("duration_ms", 0)

        # popularity (0–100)
        total_popularity += t.get("popularity", 0)

        # explicit flag
        if t.get("explicit"):
            explicit_count += 1

        # release year (release_date can be "YYYY-MM-DD" or "YYYY")
        album = t.get("album", {})
        release_date = album.get("release_date", "0000")
        year_str = release_date[:4]
        try:
            year = int(year_str)
            years.append(year)
        except ValueError:
            pass

        # artist counts
        for a in t.get("artists", []):
            name = a.get("name", "Unknown")
            artist_counts[name] = artist_counts.get(name, 0) + 1

    track_count = len(tracks)
    avg_duration_min = (total_duration_ms / track_count) / 1000 / 60
    avg_popularity = total_popularity / track_count if track_count else 0

    oldest_year = min(years) if years else "Unknown"
    newest_year = max(years) if years else "Unknown"

    # sort artists by how many times they appear
    top_artists = sorted(
        artist_counts.items(), key=lambda x: x[1], reverse=True
    )[:5]

    print("\n PLAYLIST STATISTICS")
    print("---------------------------")
    print(f"Total tracks:             {track_count}")
    print(f"Average song length:      {avg_duration_min:.1f} minutes")
    print(f"Average popularity (0–100): {avg_popularity:.1f}")
    print(f"Oldest song year:         {oldest_year}")
    print(f"Newest song year:         {newest_year}")
    print(f"Explicit tracks:          {explicit_count} / {track_count}")

    print("\n Top 5 most common artists:")
    for artist, count in top_artists:
        print(f"  {artist}: {count} track(s)")


def main():
    # Step 1: create client
    sp = create_spotify_client()

    # Step 2: extract playlist ID
    try:
        playlist_id = get_playlist_id_from_url(PLAYLIST_URL)
    except ValueError as e:
        print("Error:", e)
        return

    # Step 3: fetch playlist info
    playlist = sp.playlist(playlist_id)
    playlist_name = playlist["name"]
    owner = playlist["owner"]["display_name"]
    print(f"\nAnalyzing playlist: \"{playlist_name}\" by {owner}")

    # Step 4: fetch tracks
    tracks = get_playlist_tracks(sp, playlist_id)
    print(f"Found {len(tracks)} tracks. Calculating stats...")

    # Step 5: analyze & print (no audio_features, so no 403 errors)
    analyze_playlist(tracks)


if __name__ == "__main__":
    main()
