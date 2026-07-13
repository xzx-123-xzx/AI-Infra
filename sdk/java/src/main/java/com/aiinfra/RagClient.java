package com.aiinfra;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.Map;

public class RagClient extends BaseClient {
    public RagClient(String baseUrl, String adminToken) {
        super(baseUrl, adminToken, true);
    }

    public JsonNode health() throws Exception {
        return get("/health");
    }

    public JsonNode createKnowledgeBase(String name, String tenantId) throws Exception {
        return post("/knowledge-bases", Map.of("name", name, "tenant_id", tenantId));
    }

    public JsonNode chat(int kbId, String query) throws Exception {
        return post("/knowledge-bases/" + kbId + "/chat", Map.of("query", query));
    }

    public JsonNode getDocument(int kbId, int docId) throws Exception {
        return get("/knowledge-bases/" + kbId + "/documents/" + docId);
    }

    public JsonNode runSync(int kbId, int sourceId) throws Exception {
        return post("/knowledge-bases/" + kbId + "/sync-sources/" + sourceId + "/run", Map.of());
    }
}
