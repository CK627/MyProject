// IndexedDB 消息存储管理模块
// 实现类似微信的本地存储策略

import { Message, Conversation } from './api';

const DB_NAME = 'SmartCampusMessages';
const DB_VERSION = 1;

// 存储对象名称
const STORES = {
  MESSAGES: 'messages',           // 消息记录
  CONVERSATIONS: 'conversations', // 会话列表
  FILES: 'files',                 // 文件缓存
  METADATA: 'metadata'            // 元数据（文件引用计数等）
};

interface StoredMessage extends Message {
  conversation_id: string;  // 会话ID (userId)
  local_id?: string;        // 本地临时ID（发送中）
  send_status?: 'sending' | 'sent' | 'failed';
  deleted?: boolean;        // 软删除标记
  deleted_at?: number;      // 删除时间戳
}

interface StoredConversation extends Conversation {
  conversation_id: string;
  updated_at: number;
  pinned?: boolean;        // 置顶
  muted?: boolean;         // 免打扰
}

interface FileMetadata {
  file_id: string;         // 文件唯一标识
  url: string;             // 服务器URL
  local_url?: string;      // 本地blob URL
  size: number;
  type: string;
  reference_count: number; // 引用计数（硬链接模拟）
  downloaded: boolean;
  created_at: number;
  last_access: number;
}

class MessageStorage {
  private db: IDBDatabase | null = null;
  private readonly maxCacheSize = 500 * 1024 * 1024; // 500MB缓存上限

  // 初始化数据库
  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // 消息存储
        if (!db.objectStoreNames.contains(STORES.MESSAGES)) {
          const messageStore = db.createObjectStore(STORES.MESSAGES, { keyPath: 'id', autoIncrement: true });
          messageStore.createIndex('conversation_id', 'conversation_id', { unique: false });
          messageStore.createIndex('created_at', 'created_at', { unique: false });
          messageStore.createIndex('deleted', 'deleted', { unique: false });
        }

        // 会话存储
        if (!db.objectStoreNames.contains(STORES.CONVERSATIONS)) {
          const convStore = db.createObjectStore(STORES.CONVERSATIONS, { keyPath: 'conversation_id' });
          convStore.createIndex('updated_at', 'updated_at', { unique: false });
          convStore.createIndex('pinned', 'pinned', { unique: false });
        }

        // 文件缓存
        if (!db.objectStoreNames.contains(STORES.FILES)) {
          const fileStore = db.createObjectStore(STORES.FILES, { keyPath: 'file_id' });
          fileStore.createIndex('last_access', 'last_access', { unique: false });
        }

        // 元数据
        if (!db.objectStoreNames.contains(STORES.METADATA)) {
          db.createObjectStore(STORES.METADATA, { keyPath: 'key' });
        }
      };
    });
  }

  // ============ 消息操作 ============

  // 保存消息
  async saveMessage(message: Message, conversationId: string): Promise<void> {
    if (!this.db) await this.init();

    const storedMessage: StoredMessage = {
      ...message,
      conversation_id: conversationId,
      send_status: 'sent'
    };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.MESSAGES], 'readwrite');
      const store = transaction.objectStore(STORES.MESSAGES);
      const request = store.put(storedMessage);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  // 批量保存消息（同步服务器数据）
  async saveMessages(messages: Message[], conversationId: string): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.MESSAGES], 'readwrite');
      const store = transaction.objectStore(STORES.MESSAGES);

      messages.forEach(msg => {
        const storedMessage: StoredMessage = {
          ...msg,
          conversation_id: conversationId,
          send_status: 'sent'
        };
        store.put(storedMessage);
      });

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  }

  // 获取会话消息列表
  async getMessages(conversationId: string, limit = 50): Promise<StoredMessage[]> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.MESSAGES], 'readonly');
      const store = transaction.objectStore(STORES.MESSAGES);
      const index = store.index('conversation_id');
      const request = index.getAll(IDBKeyRange.only(conversationId));

      request.onsuccess = () => {
        const messages = request.result
          .filter((msg: StoredMessage) => !msg.deleted)
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          .slice(0, limit);
        resolve(messages);
      };
      request.onerror = () => reject(request.error);
    });
  }

  // 软删除消息（异步删除机制）
  async softDeleteMessage(messageId: number): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.MESSAGES], 'readwrite');
      const store = transaction.objectStore(STORES.MESSAGES);
      const request = store.get(messageId);

      request.onsuccess = () => {
        const message = request.result as StoredMessage;
        if (message) {
          message.deleted = true;
          message.deleted_at = Date.now();
          store.put(message);
        }
      };

      transaction.oncomplete = () => {
        // 延迟物理删除
        this.schedulePhysicalDelete();
        resolve();
      };
      transaction.onerror = () => reject(transaction.error);
    });
  }

  // 延迟物理删除（后台清理）
  private async schedulePhysicalDelete(): Promise<void> {
    // 1小时后执行物理删除
    setTimeout(() => {
      this.performPhysicalDelete();
    }, 3600000);
  }

  // 执行物理删除
  private async performPhysicalDelete(): Promise<void> {
    if (!this.db) return;

    const transaction = this.db.transaction([STORES.MESSAGES], 'readwrite');
    const store = transaction.objectStore(STORES.MESSAGES);
    const index = store.index('deleted');
    const request = index.openCursor(IDBKeyRange.only(true));

    const now = Date.now();
    const deleteThreshold = 24 * 3600000; // 24小时

    request.onsuccess = (event) => {
      const cursor = (event.target as IDBRequest).result;
      if (cursor) {
        const message = cursor.value as StoredMessage;
        if (message.deleted_at && (now - message.deleted_at > deleteThreshold)) {
          cursor.delete();
        }
        cursor.continue();
      }
    };
  }

  // ============ 会话操作 ============

  // 保存/更新会话
  async saveConversation(conversation: Conversation): Promise<void> {
    if (!this.db) await this.init();

    const stored: StoredConversation = {
      ...conversation,
      conversation_id: String(conversation.user.id),
      updated_at: Date.now()
    };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.CONVERSATIONS], 'readwrite');
      const store = transaction.objectStore(STORES.CONVERSATIONS);
      const request = store.put(stored);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  // 获取所有会话
  async getConversations(): Promise<StoredConversation[]> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.CONVERSATIONS], 'readonly');
      const store = transaction.objectStore(STORES.CONVERSATIONS);
      const request = store.getAll();

      request.onsuccess = () => {
        const conversations = request.result.sort((a: StoredConversation, b: StoredConversation) => {
          // 置顶会话优先
          if (a.pinned && !b.pinned) return -1;
          if (!a.pinned && b.pinned) return 1;
          return b.updated_at - a.updated_at;
        });
        resolve(conversations);
      };
      request.onerror = () => reject(request.error);
    });
  }

  // ============ 文件操作（硬链接模拟）============

  // 保存文件缓存
  async saveFile(fileId: string, blob: Blob, url: string): Promise<string> {
    if (!this.db) await this.init();

    const localUrl = URL.createObjectURL(blob);
    const metadata: FileMetadata = {
      file_id: fileId,
      url,
      local_url: localUrl,
      size: blob.size,
      type: blob.type,
      reference_count: 1,
      downloaded: true,
      created_at: Date.now(),
      last_access: Date.now()
    };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.FILES], 'readwrite');
      const store = transaction.objectStore(STORES.FILES);
      
      // 检查文件是否已存在（硬链接）
      const getRequest = store.get(fileId);
      
      getRequest.onsuccess = () => {
        const existing = getRequest.result as FileMetadata | undefined;
        if (existing) {
          // 文件已存在，增加引用计数
          existing.reference_count++;
          existing.last_access = Date.now();
          store.put(existing);
          resolve(existing.local_url!);
        } else {
          // 新文件，保存
          const putRequest = store.put(metadata);
          putRequest.onsuccess = () => resolve(localUrl);
          putRequest.onerror = () => reject(putRequest.error);
        }
      };
      getRequest.onerror = () => reject(getRequest.error);
    });
  }

  // 减少文件引用（删除消息时）
  async decreaseFileReference(fileId: string): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.FILES], 'readwrite');
      const store = transaction.objectStore(STORES.FILES);
      const request = store.get(fileId);

      request.onsuccess = () => {
        const metadata = request.result as FileMetadata | undefined;
        if (metadata) {
          metadata.reference_count--;
          if (metadata.reference_count <= 0) {
            // 引用计数为0，删除文件
            store.delete(fileId);
            if (metadata.local_url) {
              URL.revokeObjectURL(metadata.local_url);
            }
          } else {
            store.put(metadata);
          }
        }
        resolve();
      };
      request.onerror = () => reject(request.error);
    });
  }

  // 清理过期文件缓存
  async cleanExpiredFiles(daysOld = 30): Promise<number> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.FILES], 'readwrite');
      const store = transaction.objectStore(STORES.FILES);
      const index = store.index('last_access');
      const request = index.openCursor();

      const threshold = Date.now() - (daysOld * 24 * 3600000);
      let deletedCount = 0;

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          const metadata = cursor.value as FileMetadata;
          if (metadata.last_access < threshold) {
            if (metadata.local_url) {
              URL.revokeObjectURL(metadata.local_url);
            }
            cursor.delete();
            deletedCount++;
          }
          cursor.continue();
        } else {
          resolve(deletedCount);
        }
      };
      request.onerror = () => reject(request.error);
    });
  }

  // 获取缓存大小统计
  async getCacheStats(): Promise<{ totalSize: number; fileCount: number }> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.FILES], 'readonly');
      const store = transaction.objectStore(STORES.FILES);
      const request = store.getAll();

      request.onsuccess = () => {
        const files = request.result as FileMetadata[];
        const totalSize = files.reduce((sum, file) => sum + file.size, 0);
        resolve({ totalSize, fileCount: files.length });
      };
      request.onerror = () => reject(request.error);
    });
  }

  // 清空所有缓存
  async clearAllCache(): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(
        [STORES.MESSAGES, STORES.CONVERSATIONS, STORES.FILES],
        'readwrite'
      );

      transaction.objectStore(STORES.MESSAGES).clear();
      transaction.objectStore(STORES.CONVERSATIONS).clear();
      
      // 清理文件时释放blob URLs
      const fileStore = transaction.objectStore(STORES.FILES);
      const request = fileStore.getAll();
      request.onsuccess = () => {
        const files = request.result as FileMetadata[];
        files.forEach(file => {
          if (file.local_url) {
            URL.revokeObjectURL(file.local_url);
          }
        });
        fileStore.clear();
      };

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  }
}

// 导出单例
export const messageStorage = new MessageStorage();
