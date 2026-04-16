NewsDigest is a personal news aggregator that fetches articles from multiple RSS sources, summarizes them using Claude, and learns your reading preferences through thumbs up/down feedback.

# What it does
- Pulls articles from configurable RSS feeds (BBC, Reuters, Hacker News, etc.)
- Summarizes each article using the Claude API so you get the gist without reading the full piece
- Captures your feedback via thumbs up / thumbs down on each article
- Uses a lightweight content-based recommendation model to rank future articles based on your taste
- Persists your preference history across sessions

RSS Feeds → Article Fetcher → Claude API (summarize) → UI
                                                         ↓
                                              User feedback (👍 / 👎)
                                                         ↓
                                          Recommendation model updates
                                                         ↓
                                        Better articles ranked higher


# Author: Diego Garcia @DiegoFranGarcia