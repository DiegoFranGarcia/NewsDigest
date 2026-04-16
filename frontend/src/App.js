import { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [clusters, setClusters] = useState([]);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [ratings, setRatings] = useState({});

  useEffect(() => {
  axios.get("http://localhost:8000/clusters").then((res) => {
    setClusters(res.data);
    setLoading(false);
  });
  axios.get("http://localhost:8000/my-ratings").then((res) => {
    const ratingMap = {};
    res.data.forEach((r) => {
      ratingMap[r.article_id] = r.rating;
    });
    setRatings(ratingMap);
  });
}, []);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!search.trim()) return;
    const res = await axios.get(`http://localhost:8000/search?q=${search}`);
    setSearchResults(res.data);
  };

  const handleFeedback = async (articleId, rating) => {
  await axios.post("http://localhost:8000/feedback", {
    article_id: articleId,
    rating,
  });
  setRatings((prev) => ({ ...prev, [articleId]: rating }));
};

  const filteredClusters = clusters.filter((c) => {
    if (!c.summary) return false;
    const s = c.summary.toLowerCase();
    return (
      !s.startsWith("these articles") &&
      !s.startsWith("these article") &&
      !s.includes("distinct news events") &&
      !s.includes("do not relate to the same") &&
      !s.startsWith("i cannot") &&
      !s.startsWith("paul templer") &&
      c.summary.length > 100
    );
  });

  return (
    <div className="app">
      <header className="header">
        <div className="header-top">
          <h1>NewsDigest</h1>
          <span className="header-date">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </span>
        </div>
        <div className="header-sub">
          <span className="tagline">AI-powered summaries from across the web</span>
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              placeholder="Search articles..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
            <button type="submit" className="search-btn">Search</button>
          </form>
        </div>
      </header>

      {searchResults.length > 0 && (
        <div className="search-results">
          <h2>Search Results</h2>
          {searchResults.map((a) => (
            <div key={a.id} className="search-item">
              <a href={a.url} target="_blank" rel="noreferrer">{a.title}</a>
              <span className="source-tag">{a.source}</span>
            </div>
          ))}
          <button className="clear-btn" onClick={() => setSearchResults([])}>
            Clear results
          </button>
        </div>
      )}

      <main className="feed">
        {loading ? (
          <p className="loading">Loading your news digest...</p>
        ) : (
          filteredClusters.map((cluster) => (
            <div key={cluster.id} className="card">
              <div className="card-meta">
                <span className="source-tag">{cluster.sources.join(", ")}</span>
                <span className="article-count">{cluster.article_count} articles</span>
              </div>
              <p className="summary">{cluster.summary.replace(/^#.*\n/, "").replace(/^#+\s/gm, "").trim()}</p>
              <div className="card-actions">
                <button
                  className="expand-btn"
                  onClick={() => setExpanded(expanded === cluster.id ? null : cluster.id)}
                >
                  {expanded === cluster.id ? "Hide articles" : "View source articles"}
                </button>
                <div className="feedback-btns">
                  <button
                    onClick={() => !ratings[cluster.articles[0].id] && handleFeedback(cluster.articles[0].id, 1)}
                    className={`thumb ${ratings[cluster.articles[0].id] === 1 ? "thumb-up-active" : ""}`}
                    style={{ opacity: ratings[cluster.articles[0].id] ? 0.5 : 1, cursor: ratings[cluster.articles[0].id] ? "default" : "pointer" }}
                  >👍</button>
                  <button
                    onClick={() => !ratings[cluster.articles[0].id] && handleFeedback(cluster.articles[0].id, -1)}
                    className={`thumb ${ratings[cluster.articles[0].id] === -1 ? "thumb-down-active" : ""}`}
                    style={{ opacity: ratings[cluster.articles[0].id] ? 0.5 : 1, cursor: ratings[cluster.articles[0].id] ? "default" : "pointer" }}
                  >👎</button>
                </div>
              </div>
              {expanded === cluster.id && (
                <div className="article-list">
                  {cluster.articles.map((a) => (
                    <a key={a.id} href={a.url} target="_blank" rel="noreferrer" className="article-link">
                      <span className="article-source">{a.source}</span>
                      {a.title}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </main>
    </div>
  );
}

export default App;