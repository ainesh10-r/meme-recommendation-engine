import csv
import random
import os
from flask import Flask, jsonify, request, url_for, make_response

app = Flask(__name__, static_url_path='/static')

# --- Data Layer ---
MEMES_DATABASE = []
user_preferences = {}

# The HTML and CSS for the frontend
FRONTEND_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personalized Meme Feed</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=display:wght@400;600;700&display=swap');
        body {
            background-color: #0f172a;
            color: #e2e8f0;
            font-family: 'Tangerine', sans-serif;
            transition: all 0.3s ease-in-out;
        }
        .container {
            max-width: 1200px;
        }
        .meme-card {
            transition: transform 0.2s, box-shadow 0.2s;
            transform-origin: center center;
            animation: fadeIn 0.8s ease-out;
        }
        .meme-card:hover {
            transform: scale(1.02);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.4);
        }
        .loading-spinner {
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid #fff;
            border-radius: 50%;
            width: 48px;
            height: 48px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }
    </style>
</head>
<body class="bg-gray-900 text-gray-200 min-h-screen flex items-center justify-center p-4">

    <div class="container mx-auto p-4 flex flex-col lg:flex-row gap-8">
        <!-- Main Meme Feed -->
        <div class="flex-1">
            <h1 class="text-4xl font-bold mb-6 text-center text-teal-400">Your Meme Feed</h1>
            <div id="meme-container" class="bg-gray-800 p-6 rounded-xl shadow-lg flex flex-col items-center justify-center min-h-[400px] text-center">
                <!-- Meme content will be dynamically loaded here -->
            </div>
            
            <div id="controls" class="flex justify-center gap-4 mt-6">
                <button id="like-btn" class="flex-1 py-3 px-6 bg-green-500 hover:bg-green-600 text-white font-bold rounded-lg shadow-md transition-transform transform hover:scale-105">👍 Like</button>
                <button id="skip-btn" class="flex-1 py-3 px-6 bg-yellow-500 hover:bg-yellow-600 text-white font-bold rounded-lg shadow-md transition-transform transform hover:scale-105">⏭️ Skip</button>
            </div>
        </div>

        <!-- Recommendations Panel -->
        <div class="w-full lg:w-1/3 mt-8 lg:mt-0">
            <div class="bg-gray-800 p-6 rounded-xl shadow-lg">
                <h2 class="text-2xl font-bold mb-4 text-teal-400">Recommended for You</h2>
                <div id="recommended-memes-grid" class="space-y-4">
                    <!-- Recommended memes will be injected here -->
                </div>
            </div>
        </div>
    </div>

    <!-- Message box for user notifications -->
    <div id="message-box" class="fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center hidden z-50">
        <div class="bg-gray-800 p-8 rounded-xl shadow-2xl text-center max-w-sm">
            <p id="message-text" class="text-xl font-semibold text-gray-100 mb-4"></p>
            <button id="close-message-btn" class="bg-teal-500 hover:bg-teal-600 text-white font-bold py-2 px-6 rounded-lg">OK</button>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const userId = 'user_abc';
            const memeContainer = document.getElementById('meme-container');
            const likeButton = document.getElementById('like-btn');
            const skipButton = document.getElementById('skip-btn');
            const recommendedMemesGrid = document.getElementById('recommended-memes-grid');
            const messageBox = document.getElementById('message-box');
            const messageText = document.getElementById('message-text');
            const closeMessageButton = document.getElementById('close-message-btn');

            let allMemes = [];
            let currentMemeIndex = 0;
            let lastInteractionTime = Date.now();

            const showMessage = (message) => {
                messageText.textContent = message;
                messageBox.classList.remove('hidden');
            };

            const hideMessage = () => {
                messageBox.classList.add('hidden');
            };

            closeMessageButton.addEventListener('click', hideMessage);

            const displayMeme = (meme) => {
                lastInteractionTime = Date.now();
                const contentHtml = meme.type === 'video'
                    ? `<video controls autoplay loop class="rounded-lg shadow-lg max-h-[400px] w-full object-contain"><source src="${meme.url}" type="video/mp4"></video>`
                    : `<img src="${meme.url}" alt="${meme.title}" class="rounded-lg shadow-lg max-h-[400px] w-full object-contain">`;

                memeContainer.innerHTML = `
                    <div class="meme-card w-full">
                        ${contentHtml}
                        <div class="mt-4 text-center">
                            <h3 class="text-2xl font-bold text-gray-100">${meme.title}</h3>
                            <p class="text-sm text-gray-400">Tags: ${meme.tags.join(', ')}</p>
                        </div>
                    </div>
                `;
            };

            const fetchAndDisplayNextMeme = async () => {
                currentMemeIndex = (currentMemeIndex + 1) % allMemes.length;
                displayMeme(allMemes[currentMemeIndex]);
                await fetchRecommendations();
            };

            const postInteraction = async (action, memeId) => {
                try {
                    await fetch('/api/interact', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ user_id: userId, meme_id: memeId, action })
                    });
                } catch (error) {
                    console.error('Failed to post interaction:', error);
                }
            };

            const fetchRecommendations = async () => {
                try {
                    const response = await fetch(`/api/recommendations/${userId}`);
                    const data = await response.json();
                    renderRecommendedMemes(data.recommendations);
                } catch (error) {
                    console.error('Failed to fetch recommendations:', error);
                }
            };

            const renderRecommendedMemes = (recommendedMemes) => {
                recommendedMemesGrid.innerHTML = '';
                if (recommendedMemes.length === 0) {
                    recommendedMemesGrid.innerHTML = '<p class="text-center text-gray-500">No recommendations yet. Interact with more memes!</p>';
                    return;
                }

                recommendedMemes.slice(0, 5).forEach(meme => {
                    const card = document.createElement('div');
                    card.className = 'bg-gray-700 p-4 rounded-lg shadow-md cursor-pointer hover:bg-gray-600 transition-colors duration-200 ease-in-out';
                    
                    const thumbnailHtml = meme.type === 'video'
                        ? `<video class="w-full h-24 object-cover rounded-md mb-2"><source src="${meme.url}" type="video/mp4"></video>`
                        : `<img src="${meme.url}" alt="${meme.title}" class="w-full h-24 object-cover rounded-md mb-2">`;
                    
                    card.innerHTML = `
                        ${thumbnailHtml}
                        <h4 class="text-md font-bold text-gray-100">${meme.title}</h4>
                        <div class="flex flex-wrap gap-1 mt-1">
                            ${meme.tags.map(tag => `<span class="bg-blue-500 text-white text-xs rounded-full px-2 py-1">${tag}</span>`).join('')}
                        </div>
                    `;
                    card.onclick = () => displayMeme(meme);
                    recommendedMemesGrid.appendChild(card);
                });
            };

            likeButton.addEventListener('click', async () => {
                const currentMeme = allMemes[currentMemeIndex];
                if (!currentMeme) return;
                await postInteraction("like", currentMeme.id);
                fetchAndDisplayNextMeme();
            });

            skipButton.addEventListener('click', () => {
                fetchAndDisplayNextMeme();
            });

            // Initial data fetch
            const fetchAllMemes = async () => {
                try {
                    const response = await fetch('/api/memes');
                    const data = await response.json();
                    allMemes = data;
                    if (allMemes.length > 0) {
                        displayMeme(allMemes[0]);
                        await fetchRecommendations();
                    } else {
                        showMessage('Failed to load memes. The data file might be empty.');
                    }
                } catch (error) {
                    console.error('Failed to fetch all memes:', error);
                    showMessage('Failed to load data. Please check your backend server.');
                }
            };

            fetchAllMemes();
        });
    </script>
</body>
</html>
"""

def load_memes_from_csv():
    """
    Loads meme data from a local CSV file.
    """
    global MEMES_DATABASE
    MEMES_DATABASE = []
    
    csv_file_path = os.path.join(os.path.dirname(__file__), 'memes.csv')
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Use direct path instead of url_for for debugging
                static_url = f"/static/media/{row['url']}"
                
                MEMES_DATABASE.append({
                    "id": row["id"],
                    "url": static_url,  # Direct path
                    "title": row["title"],
                    "tags": row["tags"].strip().strip('"').split(','),
                    "type": row["type"]
                })
        
        print(f"Successfully loaded {len(MEMES_DATABASE)} memes from memes.csv.")
        
        # Debug: Show first few memes
        for meme in MEMES_DATABASE[:3]:
            print(f"Meme: {meme['title']} -> {meme['url']}")
            
    except Exception as e:
        print(f"Error: {e}")
        # Fallback data
        MEMES_DATABASE = [{"id": "test", "url": "/static/media/test.jpg", "title": "Test", "tags": ["test"], "type": "image"}]

def get_recommended_memes(user_id, count=5):
    user_prefs = user_preferences.setdefault(user_id, {"liked_memes": [], "watched_memes": {}})
    
    # If user hasn't liked anything, return random memes
    if not user_prefs["liked_memes"]:
        return random.sample(MEMES_DATABASE, min(count, len(MEMES_DATABASE)))
    
    liked_tags = {}
    for meme_id in user_prefs["liked_memes"]:
        liked_meme = next((m for m in MEMES_DATABASE if m["id"] == meme_id), None)
        if liked_meme:
            for tag in liked_meme["tags"]:
                liked_tags[tag] = liked_tags.get(tag, 0) + 1

    seen_meme_ids = set(user_prefs["watched_memes"].keys())
    unseen_memes = [m for m in MEMES_DATABASE if m["id"] not in seen_meme_ids]

    if not unseen_memes:
        # If all memes have been seen, return some random ones
        return random.sample(MEMES_DATABASE, min(count, len(MEMES_DATABASE)))

    scored_unseen = []
    for meme in unseen_memes:
        score = sum(liked_tags.get(tag, 0) for tag in meme["tags"])
        scored_unseen.append((meme, score))
    
    scored_unseen.sort(key=lambda x: x[1], reverse=True)

    # Get top recommendations
    top_recommendations = [meme for meme, score in scored_unseen[:count]]
    
    # If we don't have enough recommendations, fill with random ones
    if len(top_recommendations) < count:
        remaining = count - len(top_recommendations)
        additional = [m for m in MEMES_DATABASE if m not in top_recommendations]
        top_recommendations.extend(random.sample(additional, min(remaining, len(additional))))
    
    return top_recommendations

# --- Flask Routes ---

@app.route("/")
def serve_index():
    """
    Serves the main HTML content directly as a string.
    """
    return make_response(FRONTEND_HTML)

@app.route("/api/memes")
def get_memes():
    """
    Returns a list of all memes, primarily for initial display.
    """
    print("API call to /api/memes received.")
    try:
        return jsonify(MEMES_DATABASE)
    except Exception as e:
        print(f"Error during JSON serialization: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route("/api/recommendations/<user_id>")
def get_recommendations_route(user_id):
    """
    Returns a list of recommended memes for a specific user.
    """
    recommendations = get_recommended_memes(user_id)
    return jsonify({"recommendations": recommendations})

@app.route("/api/interact", methods=["POST"])
def interact():
    """
    Handles user interactions (like, skip, watch).
    """
    print("API call to /api/interact received.")
    data = request.json
    user_id = data.get("user_id")
    meme_id = data.get("meme_id")
    action = data.get("action")

    if not all([user_id, meme_id, action]):
        return jsonify({"status": "error", "message": "Missing data"}), 400

    user_prefs = user_preferences.setdefault(user_id, {"liked_memes": [], "watched_memes": {}})

    if action == "like":
        if meme_id not in user_prefs["liked_memes"]:
            user_prefs["liked_memes"].append(meme_id)
    elif action == "watch":
        user_prefs["watched_memes"][meme_id] = user_prefs["watched_memes"].get(meme_id, 0) + 1

    return jsonify({"status": "success", "message": "Interaction recorded."})

if __name__ == "__main__":
    print("Server starting...")
    load_memes_from_csv()
    app.run(debug=True, port=5000)