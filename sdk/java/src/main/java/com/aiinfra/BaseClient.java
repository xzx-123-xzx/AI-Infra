package com.aiinfra;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;

public class BaseClient {
    protected final String baseUrl;
    protected final String authHeader;
    protected final HttpClient client;
    protected final ObjectMapper mapper = new ObjectMapper();

    public BaseClient(String baseUrl, String token, boolean admin) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.authHeader = "Bearer " + token;
        this.client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(30)).build();
    }

    protected JsonNode request(String method, String path, String body) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(Duration.ofSeconds(120))
                .header("Authorization", authHeader);
        if (body != null) {
            builder.header("Content-Type", "application/json");
            builder.method(method, HttpRequest.BodyPublishers.ofString(body));
        } else {
            builder.method(method, HttpRequest.BodyPublishers.noBody());
        }
        HttpResponse<String> resp = client.send(builder.build(), HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() >= 400) {
            throw new RuntimeException("[" + resp.statusCode() + "] " + resp.body());
        }
        if (resp.body() == null || resp.body().isBlank()) return mapper.nullNode();
        return mapper.readTree(resp.body());
    }

    protected JsonNode get(String path) throws Exception {
        return request("GET", path, null);
    }

    protected JsonNode post(String path, Map<String, Object> payload) throws Exception {
        return request("POST", path, mapper.writeValueAsString(payload));
    }
}
