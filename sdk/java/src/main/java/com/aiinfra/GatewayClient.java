package com.aiinfra;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;
import java.util.Map;

public class GatewayClient extends BaseClient {
    public GatewayClient(String baseUrl, String adminToken) {
        super(baseUrl, adminToken, true);
    }

    public JsonNode health() throws Exception {
        return get("/health");
    }

    public JsonNode chatCompletions(String model, List<Map<String, String>> messages) throws Exception {
        return post("/v1/chat/completions", Map.of("model", model, "messages", messages, "stream", false));
    }

    public JsonNode listTenants() throws Exception {
        return get("/admin/tenants");
    }

    public JsonNode tenantUsage(String tenantId) throws Exception {
        return get("/admin/tenants/" + tenantId + "/usage");
    }
}
