# AI-Infra Java SDK

```java
RagClient rag = new RagClient("http://localhost:8081", adminToken);
JsonNode kb = rag.createKnowledgeBase("手册", "team-a");
JsonNode answer = rag.chat(kb.get("id").asInt(), "AI中台是什么？");
```

Build: `mvn -f sdk/java package`
