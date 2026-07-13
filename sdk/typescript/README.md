# AI-Infra TypeScript SDK

```bash
cd sdk/typescript && npm install && npm run build
```

```typescript
import { GatewayClient, RagClient, AgentClient } from '@aiinfra/sdk';

const rag = new RagClient('http://localhost:8081', { adminToken: 'xxx' });
const doc = await rag.uploadDocument(1, fileBlob, 'readme.md');
const status = await rag.getDocument(1, doc.id);
```
