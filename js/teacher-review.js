import jsPreviewExcel from '/static/lib/js-preview-excel/index.min.js';

const params = new URLSearchParams(window.location.search);
const fileId = params.get('fileId');
const project = params.get('project');

if (!fileId || !project) {
  alert('缺少参数');
  window.close();
}

const previewContainer = document.getElementById('preview-content');
// const reviewSelect = document.getElementById('review-result'); // Removed
const annoTextarea = document.getElementById('review-annotation');
const btnSave = document.getElementById('btn-save-draft');
const btnPass = document.getElementById('btn-pass');
const btnReject = document.getElementById('btn-reject');
const btnClose = document.getElementById('btn-close');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const reviewProgress = document.getElementById('review-progress');
const autoNextCheckbox = document.getElementById('auto-next');

let currentFile = null;
let reviewList = [];
let currentIndex = -1;

// Load review list from storage
try {
    const storedProject = localStorage.getItem('reviewProject');
    // We allow reading if projects match, or if we just want to try our luck (though strict matching is safer)
    if (storedProject === project) {
        reviewList = JSON.parse(localStorage.getItem('reviewList') || '[]');
    }
} catch (e) {
    console.error('Failed to parse review list', e);
}

// Initialize
(async function() {
  updateNavUI();

  // Fetch file info
  const res = await fetch(`/api/filestat_list.php?studentID=${fileId}&type=${project}`);
  const data = res.ok ? await res.json() : null;
  
  if (!data || !data.items || data.items.length === 0) {
    previewContainer.innerHTML = '未找到文件记录';
    return;
  }
  
  const item = data.items[0];
  const submittedKey = project + 'Submitted';
  const pathKey = project + 'Path';
  const reviewKey = project + 'ReviewResult';
  const annoKey = project + 'Annotation';
  
  if (!item[submittedKey]) {
    previewContainer.innerHTML = '该学生尚未提交文件';
    return;
  }
  
  currentFile = {
    path: item[pathKey],
    review: item[reviewKey] || '未批阅',
    annotation: item[annoKey] || ''
  };
  
  // Update local list status if it differs (sync)
  if (currentIndex !== -1 && reviewList[currentIndex]) {
      reviewList[currentIndex].reviewResult = currentFile.review;
      reviewList[currentIndex].isSubmitted = true; // Confirmed by API
      updateNavUI(); // Re-calc counts
      localStorage.setItem('reviewList', JSON.stringify(reviewList));
  }

  // Set review status (removed dropdown logic)
  // reviewSelect.value = currentFile.review;
  
  // Set annotation
  if (annoTextarea) annoTextarea.value = currentFile.annotation;
  
  // Load file preview
  await loadPreview(currentFile.path);

  // 启动 Session 监控
  if (typeof startSessionMonitor === 'function') {
    startSessionMonitor(30000);
  }
})();

function updateNavUI() {
    if (btnPrev) btnPrev.disabled = true;
    if (btnNext) btnNext.disabled = true;

    if (reviewList.length === 0) return;

    // Find current index by studentID (fileId)
    // Ensure both are treated as strings
    const targetId = String(fileId).trim();
    currentIndex = reviewList.findIndex(it => String(it.username).trim() === targetId);
    
    // Calculate pending count
    const pendingCount = reviewList.filter(it => it.isSubmitted && it.reviewResult === '未批阅').length;
    const totalPendingInList = reviewList.filter(it => it.isSubmitted).length; // Or just reviewList.length depending on context, but user said "current review / total need review"
    
    // Actually user requirement: "Current / Total" (implied: current index / total count OR current progress / total pending)
    // "span 换一个样式：当前审批的/全部需要审批的" -> "Current Index / Total Count" makes most sense for navigation context
    // BUT "全部需要审批的" usually means pending count.
    // Let's interpret as: "Pending: X / Total: Y" or "Progress: X / Y"
    // Let's go with "待审批: X / 总提交: Y" to be clear and helpful.
    // Wait, user said "当前审批的/全部需要审批的". 
    // Maybe "Index+1 / Total"?
    // Let's stick to "待审批: N" but maybe add total context?
    // Let's try: "待审批: N / 总共: M"
    
    if (reviewProgress) {
        // reviewProgress.textContent = `剩余待审批: ${pendingCount}`;
        reviewProgress.textContent = `待审批: ${pendingCount} / 总提交: ${totalPendingInList}`;
    }

    if (currentIndex === -1) return;

    // Determine Prev/Next availability
    // Optimization: Skip non-pending/submitted items when clicking Next/Prev if not in pending mode?
    // User req 4: "优化，如果不在文件统计提交管理里面就筛选好提交且未审批的，直接点击审批批阅按钮，虽然显示剩余审批6个，但是点击下一个还是会出现未提交的和提交了但是已经审批过的"
    // This implies that Next/Prev should SKIP processed/unsubmitted items.
    
    if (btnPrev) {
        // Find previous VALID item
        const prevIndex = findPrevValidIndex(currentIndex);
        btnPrev.disabled = prevIndex === -1;
        btnPrev.onclick = () => navigateTo(prevIndex);
    }
    if (btnNext) {
        // Find next VALID item
        const nextIndex = findNextValidIndex(currentIndex);
        btnNext.disabled = nextIndex === -1;
        btnNext.onclick = () => navigateTo(nextIndex);
    }
}

function findPrevValidIndex(curr) {
    for (let i = curr - 1; i >= 0; i--) {
        const it = reviewList[i];
        // We want to navigate to ANY submitted item? Or only PENDING items?
        // User said: "点击下一个还是会出现未提交的和提交了但是已经审批过的" -> implying they DON'T want to see those.
        // So they ONLY want to see "Submitted AND Pending".
        if (it.isSubmitted && it.reviewResult === '未批阅') {
            return i;
        }
    }
    return -1;
}

function findNextValidIndex(curr) {
    for (let i = curr + 1; i < reviewList.length; i++) {
        const it = reviewList[i];
        if (it.isSubmitted && it.reviewResult === '未批阅') {
            return i;
        }
    }
    return -1;
}

function navigateTo(index) {
    if (index < 0 || index >= reviewList.length) return;
    const nextUser = reviewList[index].username;
    window.location.href = `teacher_review.html?fileId=${nextUser}&project=${project}`;
}

function findNextPendingIndex() {
    for (let i = currentIndex + 1; i < reviewList.length; i++) {
        const it = reviewList[i];
        if (it.isSubmitted && it.reviewResult === '未批阅') {
            return i;
        }
    }
    return -1;
}

async function loadPreview(path) {
  const ext = path.split('.').pop().toLowerCase();
  
    if (['doc', 'docx', 'xls', 'xlsx'].includes(ext)) {
        try {
            if (['doc', 'docx'].includes(ext)) {
                if (ext === 'doc') {
                    throw new Error('Legacy .doc format requires server-side conversion');
                }

                previewContainer.innerHTML = '<div style="padding:20px">正在加载 Word 文档...</div>';
                
                const fileRes = await fetch(encodeURI(path));
                if (!fileRes.ok) throw new Error('File fetch failed');
                const arrayBuffer = await fileRes.arrayBuffer();
                
                if (typeof docx === 'undefined') {
                     throw new Error('docx-preview library not loaded');
                }

                previewContainer.innerHTML = '<div id="docx-container" style="background:#fff; height:100%; overflow:auto;"></div>';
                const container = document.getElementById('docx-container');
                
                await docx.renderAsync(arrayBuffer, container, null, {
                    className: "docx", 
                    inWrapper: true,
                    ignoreWidth: false,
                    ignoreHeight: false,
                    breakPages: true
                });

            } else {
                 previewContainer.innerHTML = '<div style="padding:20px">正在加载 Excel 文档...</div>';
                 const fileRes = await fetch(encodeURI(path));
                 if (!fileRes.ok) throw new Error('File fetch failed');
                 const arrayBuffer = await fileRes.arrayBuffer();

                 if (!jsPreviewExcel || !jsPreviewExcel.init) {
                     throw new Error('@js-preview/excel library not loaded correctly');
                 }

                 previewContainer.innerHTML = '<div id="excel-container" style="width:100%;height:100%;"></div>';
                 const excelContainer = document.getElementById('excel-container');
                 
                 const excelInstance = jsPreviewExcel.init(excelContainer);
                 await excelInstance.preview(arrayBuffer);
            }
        } catch (e) {
             console.warn('Local preview failed, falling back to PDF conversion', e);
             startConversion(path);
         }
    } else if (ext === 'pdf') {
    const viewerUrl = `/static/pdfjs/web/viewer.html?file=${encodeURIComponent(path)}`;
    // Decode URI component for display in case user inspects, but encodeURIComponent handles the actual URL param correctly.
    // However, if 'path' itself was already encoded (e.g. from DB), double encoding might be an issue.
    // Based on the log, the path seems raw with Chinese chars.
    previewContainer.innerHTML = `<iframe src="${viewerUrl}" class="iframe-viewer"></iframe>`;
  } else {
    startConversion(path);
  }
}

async function startConversion(path) {
  previewContainer.innerHTML = '<div>正在转换文件... <span id="progress-text">0%</span></div>';
  const loadingBar = document.getElementById('loading-bar');
  
  try {
    const res = await fetch('/api/convert/toPdf.php', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ filePath: path })
    });
    
    if (res.status === 202) {
      const data = await res.json();
      pollStatus(data.taskId);
    } else {
      previewContainer.innerHTML = '转换请求失败';
    }
  } catch (e) {
    previewContainer.innerHTML = '转换错误: ' + e.message;
  }
}

async function pollStatus(taskId) {
  const loadingBar = document.getElementById('loading-bar');
  const progressText = document.getElementById('progress-text');
  
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/convert/status.php?taskId=${taskId}`);
      const data = await res.json();
      
      if (data.progress) {
        loadingBar.style.width = data.progress + '%';
        if (progressText) progressText.innerText = data.progress + '%';
      }
      
      if (data.status === 'completed') {
        clearInterval(interval);
        const viewerUrl = `/static/pdfjs/web/viewer.html?file=${encodeURIComponent(data.pdfUrl)}`;
        previewContainer.innerHTML = `<iframe src="${viewerUrl}" class="iframe-viewer"></iframe>`;
      } else if (data.status === 'failed') {
        clearInterval(interval);
        previewContainer.innerHTML = '转换失败';
      }
    } catch (e) {
      clearInterval(interval);
      previewContainer.innerHTML = '轮询错误';
    }
  }, 1000);
}

// Events
// Helper for submission
async function submitReview(result) {
  const anno = annoTextarea ? annoTextarea.value : '';
  
  const res = await fetch('/api/review/result/update.php', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ studentID: fileId, project: project, result: result, annotation: anno })
  });
  const data = res.ok ? await res.json() : null;
  if (data && data.success) {
    // alert('提交成功');
    
    // Update local state
    if (currentIndex !== -1 && reviewList[currentIndex]) {
        reviewList[currentIndex].reviewResult = result;
        localStorage.setItem('reviewList', JSON.stringify(reviewList));
    }

    if (window.opener && window.opener.refreshFileStat) {
      window.opener.refreshFileStat();
    }

    // Auto Next Logic
    if (autoNextCheckbox && autoNextCheckbox.checked) {
        // Since current item is now reviewed, findNextPendingIndex will naturally skip it
        // We use the new logic: find next PENDING item
        const nextIndex = findNextValidIndex(currentIndex);
        if (nextIndex !== -1) {
            navigateTo(nextIndex);
        } else {
            alert('已完成当前项目的所有待办事项');
            window.close();
        }
    } else {
        window.close();
    }

  } else {
    alert('提交失败');
  }
}

if (btnPass) btnPass.addEventListener('click', () => submitReview('通过'));
if (btnReject) btnReject.addEventListener('click', () => submitReview('不通过'));
// btnSubmit.addEventListener('click', async () => { ... }); // Removed old handler

btnClose.addEventListener('click', () => {
  window.close();
});

btnSave.addEventListener('click', () => {
    alert('草稿已保存 (Mock)');
});
