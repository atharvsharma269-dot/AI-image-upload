from pymongo import MongoClient
from datetime import datetime

MONGO_URI = "mongodb+srv://atharvsharma269_db_user:Backend123@ai-quality-cluster.nzhzevk.mongodb.net/?appName=ai-quality-cluster&retryWrites=true&w=majority"

client = MongoClient(MONGO_URI)

db = client["ai_quality_db"]
results_collection = db["analysis_results"]


# -----------------------------
# Save Analysis
# -----------------------------
def save_analysis(data):
    data["timestamp"] = datetime.utcnow()
    results_collection.insert_one(data)


# -----------------------------
# Get Previous Quality Scores
# -----------------------------
def get_user_scores(user_id):
    records = results_collection.find({"user_id": user_id})
    return [record["quality_score"] for record in records]


# -----------------------------
# User Detailed Analytics
# -----------------------------
def get_user_analysis(user_id):
    records = list(results_collection.find({"user_id": user_id}))

    if not records:
        return None

    total_tasks = len(records)
    quality_scores = [r["quality_score"] for r in records]
    latest_quality_score = records[-1]["quality_score"]

    fraud_attempts = sum(
        1 for r in records
        if r["completion_status"] == "Fraud Detected - Same Image Uploaded"
    )

    average_quality_score = round(sum(quality_scores) / total_tasks, 2)

    trust_score = round(
        max(average_quality_score - fraud_attempts * 5, 0),
        2
    )

    return {
        "user_id": user_id,
        "total_tasks": total_tasks,
        "average_quality_score": average_quality_score,
        "latest_quality_score": latest_quality_score,
        "fraud_attempts": fraud_attempts,
        "trust_score": trust_score
    }


# -----------------------------
# Leaderboard (Mongo Aggregation)
# -----------------------------
def get_leaderboard(top_n=5):
    pipeline = [
        {
            "$group": {
                "_id": "$user_id",
                "total_tasks": {"$sum": 1},
                "average_quality_score": {"$avg": "$quality_score"},
                "fraud_attempts": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$completion_status", "Fraud Detected - Same Image Uploaded"]},
                            1,
                            0
                        ]
                    }
                }
            }
        },
        {
            "$addFields": {
                "trust_score": {
                    "$subtract": [
                        {"$round": ["$average_quality_score", 2]},
                        {"$multiply": ["$fraud_attempts", 5]}
                    ]
                }
            }
        },
        {
            "$sort": {"trust_score": -1}
        },
        {
            "$limit": top_n
        }
    ]

    results = list(results_collection.aggregate(pipeline))

    leaderboard = []

    for r in results:
        leaderboard.append({
            "user_id": r["_id"],
            "total_tasks": r["total_tasks"],
            "average_quality_score": round(r["average_quality_score"], 2),
            "fraud_attempts": r["fraud_attempts"],
            "trust_score": round(max(r["trust_score"], 0), 2)
        })

    return leaderboard
def get_admin_analytics():
    # Total tasks
    total_tasks = results_collection.count_documents({})

    if total_tasks == 0:
        return None

    # Total unique users
    total_users = len(results_collection.distinct("user_id"))

    # Platform average quality
    pipeline_avg = [
        {
            "$group": {
                "_id": None,
                "average_quality": {"$avg": "$quality_score"}
            }
        }
    ]

    avg_result = list(results_collection.aggregate(pipeline_avg))
    average_quality_platform = round(avg_result[0]["average_quality"], 2)

    # Fraud count
    fraud_count = results_collection.count_documents({
        "completion_status": "Fraud Detected - Same Image Uploaded"
    })

    fraud_rate_percent = round((fraud_count / total_tasks) * 100, 2)

    # Leaderboard aggregation
    pipeline_leaderboard = [
        {
            "$group": {
                "_id": "$user_id",
                "average_quality": {"$avg": "$quality_score"},
                "fraud_attempts": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$completion_status", "Fraud Detected - Same Image Uploaded"]},
                            1,
                            0
                        ]
                    }
                }
            }
        },
        {
            "$addFields": {
                "trust_score": {
                    "$subtract": [
                        {"$round": ["$average_quality", 2]},
                        {"$multiply": ["$fraud_attempts", 5]}
                    ]
                }
            }
        }
    ]

    leaderboard = list(results_collection.aggregate(pipeline_leaderboard))

    # Compute best and worst
    leaderboard_clean = [
        {
            "user_id": r["_id"],
            "trust_score": round(max(r["trust_score"], 0), 2)
        }
        for r in leaderboard
    ]

    leaderboard_sorted = sorted(
        leaderboard_clean,
        key=lambda x: x["trust_score"],
        reverse=True
    )

    top_performer = leaderboard_sorted[0]
    lowest_performer = leaderboard_sorted[-1]

    return {
        "total_users": total_users,
        "total_tasks": total_tasks,
        "average_quality_platform": average_quality_platform,
        "fraud_rate_percent": fraud_rate_percent,
        "top_performer": top_performer,
        "lowest_performer": lowest_performer
    }
