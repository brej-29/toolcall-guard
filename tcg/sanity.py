"""Phase 0: one tiny gemini-3.8-flash call in location global against the .env project."""
from tcg import config, costs, gemini

if __name__ == "__main__":
    c = gemini._client()
    print("client project:", c._api_client.project, "| location:", c._api_client.location,
          "| quota project:", config.credentials().quota_project_id)
    r = gemini.generate("Reply with exactly the word OK.", phase="p0-sanity")
    print("text:", repr(r["text"]), "| latency_s:", r["latency_s"])
    print("usage:", r["usage"])
    print("model version:", r["response"].get("model_version"), "| response id:", r["response"].get("response_id"))
    costs.main()
