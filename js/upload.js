/**
 * 分片上传工具
 * 提供 uploadFileChunked 与 uploadFilesChunked，两者均使用 FormData 逐分片发送到后端。
 * 设计目标：绕过服务器的 post_max_size / upload_max_filesize 限制，实现大文件上传。
 * 新增功能：支持断点续传，上传前检查已上传分片。
 * 
 * 依赖: js/index.js (公共库 - CHUNK_SIZE, genUploadId, genStableUploadId, isHiddenFile, dirname, joinPath, safeJson)
 */

// 以下常量和函数已移至 js/index.js:
// - CHUNK_SIZE
// - genUploadId
// - genStableUploadId
// - isHiddenFile
// - dirname
// - joinPath
// - safeJson

/**
 * 是否启用断点续传
 */
const ENABLE_RESUME = true;

/**
 * 检查已上传的分片（断点续传）
 * @param {string} username
 * @param {string} uploadId
 * @returns {Promise<number[]>} 已上传的分片索引数组
 */
async function checkUploadedChunks(username, uploadId) {
  try {
    const res = await fetch('/api/check_chunks.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, upload_id: uploadId })
    });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.uploaded_chunks) ? data.uploaded_chunks : [];
  } catch {
    return [];
  }
}

/**
 * 分片上传单个文件（支持断点续传）
 * @param {File} file 要上传的文件
 * @param {string} username 纯数字用户名
 * @param {string} dir 目标相对目录（可空）
 * @param {number} chunkSize 分片大小（字节）
 * @param {(p:number)=>void} [onProgress] 进度回调（0-1）
 * @param {boolean} [enableResume=true] 是否启用断点续传
 * @returns {Promise<{ok:boolean,name:string,path?:string,error?:string,resumed?:boolean}>}
 */
async function uploadFileChunked(file, username, dir, chunkSize = CHUNK_SIZE, onProgress, enableResume = ENABLE_RESUME) {
  const total = Math.ceil(file.size / chunkSize) || 1;
  
  // 断点续传：使用稳定的 uploadId
  const uploadId = enableResume ? genStableUploadId(file, username) : genUploadId();
  
  // 检查已上传的分片
  let uploadedSet = new Set();
  let resumed = false;
  if (enableResume) {
    const uploadedChunks = await checkUploadedChunks(username, uploadId);
    uploadedSet = new Set(uploadedChunks);
    if (uploadedSet.size > 0) {
      resumed = true;
      console.log(`[断点续传] ${file.name}: 已上传 ${uploadedSet.size}/${total} 分片`);
    }
  }
  
  for (let i = 0; i < total; i++) {
    // 跳过已上传的分片
    if (uploadedSet.has(i)) {
      if (onProgress) onProgress((i + 1) / total);
      continue;
    }
    
    const start = i * chunkSize;
    const end = Math.min(file.size, start + chunkSize);
    const blob = file.slice(start, end);
    const fd = new FormData();
    fd.append('username', username);
    fd.append('dir', dir || '');
    fd.append('filename', file.name);
    fd.append('upload_id', uploadId);
    fd.append('chunk_index', String(i));
    fd.append('total_chunks', String(total));
    fd.append('chunk', blob, `${file.name}.part${i}`);
    const res = await fetch('/api/upload_chunk.php', { method: 'POST', credentials: 'include', body: fd });
    if (!res.ok) {
      const err = await safeJson(res);
      return { ok: false, name: file.name, error: (err && err.error) || '分片上传失败' };
    }
    const data = await res.json();
    if (onProgress) onProgress((i + 1) / total);
    if (i === total - 1) {
      if (data && data.ok) return { ok: true, name: file.name, path: data.path, resumed };
      return { ok: false, name: file.name, error: (data && data.error) || '合并失败' };
    }
  }
  
  // 如果所有分片都已上传，需要触发合并（发送最后一片）
  if (uploadedSet.size === total) {
    // 重新发送最后一片以触发合并
    const lastIdx = total - 1;
    const start = lastIdx * chunkSize;
    const end = Math.min(file.size, start + chunkSize);
    const blob = file.slice(start, end);
    const fd = new FormData();
    fd.append('username', username);
    fd.append('dir', dir || '');
    fd.append('filename', file.name);
    fd.append('upload_id', uploadId);
    fd.append('chunk_index', String(lastIdx));
    fd.append('total_chunks', String(total));
    fd.append('chunk', blob, `${file.name}.part${lastIdx}`);
    const res = await fetch('/api/upload_chunk.php', { method: 'POST', credentials: 'include', body: fd });
    const data = await safeJson(res);
    if (data && data.ok) return { ok: true, name: file.name, path: data.path, resumed: true };
    return { ok: false, name: file.name, error: (data && data.error) || '合并失败' };
  }
  
  return { ok: false, name: file.name, error: '未知错误' };
}

/**
 * 批量分片上传
 * @param {FileList|File[]} files 文件列表
 * @param {string} username 用户名
 * @param {string} dir 目标相对目录
 * @param {(current:number,total:number)=>void} [onProgress] 整体进度
 * @returns {Promise<Array<{ok:boolean,name:string,path?:string,error?:string}>>}
 */
async function uploadFilesChunked(files, username, dir, onProgress, skipHidden = true) {
  const listAll = Array.from(files || []);
  const list = skipHidden ? listAll.filter(f => !isHiddenFile(f)) : listAll;
  const total = list.length;
  const results = [];
  for (let i = 0; i < total; i++) {
    const f = list[i];
    const r = await uploadFileChunked(f, username, dir, undefined, p => {
      if (onProgress) onProgress(i + p, total);
    });
    results.push(r);
  }
  return results;
}

/**
 * 分片上传整个文件夹（根据 webkitRelativePath 还原结构）
 * @param {FileList|File[]} files 文件列表（来自目录选择）
 * @param {string} username 用户名
 * @param {string} baseDir 目标基础目录（当前所在目录）
 * @param {(current:number,total:number)=>void} [onProgress] 整体进度
 * @returns {Promise<Array<{ok:boolean,name:string,path?:string,error?:string}>>}
 */
async function uploadFolderChunked(files, username, baseDir, onProgress, skipHidden = true) {
  const listAll = Array.from(files || []);
  const list = skipHidden ? listAll.filter(f => !isHiddenFile(f)) : listAll;
  const total = list.length;
  const results = [];
  for (let i = 0; i < total; i++) {
    const f = list[i];
    const rel = (f.webkitRelativePath || '').trim();
    const dir = joinPath(baseDir, dirname(rel));
    const r = await uploadFileChunked(f, username, dir, undefined, p => {
      if (onProgress) onProgress(i + p, total);
    });
    results.push(r);
  }
  return results;
}