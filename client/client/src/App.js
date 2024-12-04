import { useState, useEffect } from "react";
import "./App.css";

const SERVER_URL = "http://127.0.0.1:5000";

function App() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState(null);
  const [twitterHandle, setTwitterHandle] = useState("");

  useEffect(() => {
    document.body.style.backgroundColor = "#1a1a1a";
    return () => {
      document.body.style.backgroundColor = "";
    };
  }, []);

  const handleCompare = () => {
    if (!twitterHandle) return;
    const cleanedHandle = twitterHandle.replace("@", "").trim();

    fetch(`${SERVER_URL}/compare/${cleanedHandle}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log(data);
        setMessage("Comparison complete");
        setError(null);
      })
      .catch((error) => {
        console.error("Error:", error);
        setError("Failed to help you make a friend");
      });
  };

  return (
    <div className="App">
      <div className="comparison-container">
        <span className="comparison-text">What do I have in common with</span>
        <input
          type="text"
          className="twitter-handle-input"
          placeholder="Twitter handle"
          value={twitterHandle}
          onChange={(e) => setTwitterHandle(e.target.value)}
        />
        <button className="go-button" onClick={handleCompare}>
          Go
        </button>
      </div>
      {error && <div className="error-message">{error}</div>}
      <div className="results-container"></div>
    </div>
  );
}

export default App;
