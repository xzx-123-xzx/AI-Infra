package com.aiinfra;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.HashMap;
import java.util.Map;

public class AgentClient extends BaseClient {
    public AgentClient(String baseUrl, String adminToken) {
        super(baseUrl, adminToken, true);
    }

    public JsonNode run(String query, Integer kbId) throws Exception {
        Map<String, Object> payload = new HashMap<>();
        payload.put("query", query);
        if (kbId != null) payload.put("kb_id", kbId);
        return post("/agents/run", payload);
    }
}
