/**
 * 文件页面 - 毕业模块 (Vue 重构版)
 * 包含：毕业论文/实习证明及其他文件上传、状态加载
 * 
 * 依赖: js/index.js, js/vue.global.js, js/files-core.js
 */

const { createApp, ref, onMounted } = Vue;

let gradAppInstance = null;

const moduleConfig = [
  { id: 'grad', title: '自行联系岗位实习单位申请表提交', api: '/api/upload_universal.php', fileType: 'thesis', keySubmitted: 'thesisSubmitted', keyPath: 'thesisPath', keyTime: 'thesisFinalSubmissionTime', accept: '.pdf', template: '/template/浙江工商职业技术学院学生自行联系岗位实习单位申请表（模板）.docx' },
  { id: 'intern', title: '学生岗位三方协议书提交', api: '/api/upload_universal.php', fileType: 'internship', keySubmitted: 'internshipSubmitted', keyPath: 'internshipPath', keyTime: 'internshipFinalSubmissionTime', accept: '.pdf', template: '/template/学生岗位实习三方协议书（模板）.docx' },
  { id: 'opinion', title: '实习单位意见提交', api: '/api/upload_universal.php', fileType: 'opinion', keySubmitted: 'opinionSubmitted', keyPath: 'opinionPath', keyTime: 'opinionFinalSubmissionTime', accept: '.pdf', template: '/template/实习单位意见（模板）.docx' },
  { id: 'commitment', title: '实习自主住宿承诺书及家长意见提交', api: '/api/upload_universal.php', fileType: 'commitment', keySubmitted: 'commitmentSubmitted', keyPath: 'commitmentPath', keyTime: 'commitmentFinalSubmissionTime', accept: '.pdf', template: '/template/学生实习自主住宿承诺书及家长意见（模板）.docx' },
  { id: 'parental', title: '家长意见提交', api: '/api/upload_universal.php', fileType: 'parental', keySubmitted: 'parentalSubmitted', keyPath: 'parentalPath', keyTime: 'parentalFinalSubmissionTime', accept: '.pdf', template: '/template/家长意见（模板）.docx' },
  { id: 'guardian', title: '丙方实习岗位实习法定监护人（或家长）知情同意书提交', api: '/api/upload_universal.php', fileType: 'guardian', keySubmitted: 'guardianSubmitted', keyPath: 'guardianPath', keyTime: 'guardianFinalSubmissionTime', accept: '.pdf', template: '/template/丙方岗位实习法定监护人（或家长）知情同意书 .docx' },
  { id: 'report', title: '学生实习企业考察报告表提交', api: '/api/upload_universal.php', fileType: 'report', keySubmitted: 'reportSubmitted', keyPath: 'reportPath', keyTime: 'reportFinalSubmissionTime', accept: '.pdf', template: '/template/浙江工商职业技术学院学生实习企业考察报告表 （模板）.doc' },
  { id: 'summary', title: '学生实习企业考察情况汇总表提交', api: '/api/upload_universal.php', fileType: 'summary', keySubmitted: 'summarySubmitted', keyPath: 'summaryPath', keyTime: 'summaryFinalSubmissionTime', accept: '.doc,.docx', template: '/template/学院学生实习企业考察情况汇总表（模板）.docx' },
  { id: 'license', title: '企业营业执照提交', api: '/api/upload_universal.php', fileType: 'license', keySubmitted: 'licenseSubmitted', keyPath: 'licensePath', keyTime: 'licenseFinalSubmissionTime', accept: '.pdf' },
  { id: 'credit', title: '企业信用报告提交', api: '/api/upload_universal.php', fileType: 'credit', keySubmitted: 'creditSubmitted', keyPath: 'creditPath', keyTime: 'creditFinalSubmissionTime', accept: '.pdf' },
  { id: 'safety', title: '毕业实习安全责任书提交', api: '/api/upload_universal.php', fileType: 'safety', keySubmitted: 'safetySubmitted', keyPath: 'safetyPath', keyTime: 'safetyFinalSubmissionTime', accept: '.pdf' },
  { id: 'assessment', title: '岗位实习报告及考核表提交', api: '/api/upload_universal.php', fileType: 'assessment', keySubmitted: 'assessmentSubmitted', keyPath: 'assessmentPath', keyTime: 'assessmentFinalSubmissionTime', accept: '.doc,.docx', desc: '本报告需实习单位盖章，并请按既定框架模板填写', template: '/template/岗位实习报告及考核表（模板）.docx' },
  { id: 'names_summary', title: '实习学生信息及指导教师名单汇总表提交', api: '/api/upload_universal.php', fileType: 'names_summary', keySubmitted: 'names_summarySubmitted', keyPath: 'names_summaryPath', keyTime: 'names_summaryFinalSubmissionTime', accept: '.xls,.xlsx', template: '/template/浙江工商职业技术学院实习学生信息及指导教师名单汇总表.xlsx' }
];

const gradApp = createApp({
  setup() {
    const modules = ref(moduleConfig.map(c => ({
      ...c,
      filename: '',
      uploading: false,
      progress: 0,
      progressText: '',
      message: '仅允许提交一个文件，且不可重复提交',
      msgClass: '',
      finalTime: '',
      submitted: false,
      dragover: false
    })));

    const files = {};
    const currentUser = ref(null);

    const handleFileSelect = (event, id) => {
      const file = event.target.files[0];
      if (!file) return;
      files[id] = file;
      const mod = modules.value.find(m => m.id === id);
      if (mod) {
        mod.filename = file.name;
        mod.msgClass = '';
      }
    };

    const triggerUpload = (id) => {
        const input = document.getElementById(id + '-file');
        if (input) input.click();
    };

    const handleDrop = (event, id) => {
       const file = event.dataTransfer.files[0];
       const mod = modules.value.find(m => m.id === id);
       if (mod) mod.dragover = false;
       if (!file) return;
       files[id] = file;
       if (mod) {
         mod.filename = file.name;
         mod.msgClass = '';
       }
    };

    const submitFile = async (id) => {
        const file = files[id];
        const mod = modules.value.find(m => m.id === id);
        if (!mod) return;
        
        if (!file && !mod.submitted) {
            mod.message = '请先选择要提交的文件';
            mod.msgClass = 'message error';
            return;
        }
        // 如果已提交且没有新文件，提示
        if (!file && mod.submitted) {
             mod.message = '请选择新文件以更新提交';
             mod.msgClass = 'message error';
             return;
        }

        try {
            mod.uploading = true;
            mod.progress = 0;
            mod.progressText = mod.submitted ? '更新中' : '提交中';
            mod.message = mod.submitted ? '正在更新...' : '正在提交...';
            mod.msgClass = '';

            const ok = await uploadGenericChunked(mod.api, file, currentUser.value.username, true, mod.fileType, (p) => {
                mod.progress = Math.floor(p * 100);
                mod.progressText = `${mod.submitted ? '更新' : '提交'}中（${mod.progress}%）`;
            });

            if (ok) {
                mod.message = mod.submitted ? '更新成功' : '提交成功';
                mod.msgClass = 'message success';
                mod.filename = ''; // Reset filename display to '已提交...' via loadStatus
                files[id] = null;  // Clear file
                const input = document.getElementById(id + '-file');
                if (input) input.value = '';
                await loadStatus(); // Reload status
            } else {
                mod.message = '提交失败';
                mod.msgClass = 'message error';
            }
        } catch (e) {
            console.error(e);
            mod.message = '提交异常';
            mod.msgClass = 'message error';
        } finally {
            mod.uploading = false;
            mod.progress = 0;
            mod.progressText = '';
        }
    };
    
    const loadConfig = async () => {
        try {
            const res = await fetch('/api/graduation_config_public.php', { method: 'GET' });
            const data = res.ok ? await res.json() : null;
            
            if (data && data.ok && data.config) {
                modules.value.forEach(mod => {
                    // Match module fileType (e.g. 'thesis') to config key
                    const conf = data.config[mod.fileType];
                    if (conf && conf.allowed_extensions && conf.allowed_extensions.length > 0) {
                        // Update accept attribute: .pdf, .doc, ...
                        mod.accept = '.' + conf.allowed_extensions.join(',.');
                    }
                });
            }
        } catch (e) {
            console.error('Failed to load upload config', e);
        }
    };

    const loadStatus = async () => {
       await loadConfig(); // Load config first
       if (!currentUser.value) return;
       const username = currentUser.value.username;
       try {
         // Use the new API to get full status for the current user
         const res = await fetch('/api/get_my_status.php', { method: 'GET', credentials: 'include' });
         const data = res.ok ? await res.json() : null;
         
         const me = (data && data.ok && data.item) ? data.item : null;
         
         if (me) {
             modules.value.forEach(mod => {
                 const isSub = !!me[mod.keySubmitted];
                 mod.submitted = isSub;
                 if (isSub) {
                     const path = String(me[mod.keyPath] || '');
                     const fname = path.split('/').pop();

                     // Use fileType as the key prefix because backend uses config keys (thesis, internship, etc.)
                     // which correspond to fileType in our moduleConfig.
                     const keyPrefix = mod.fileType; 
                     const review = me[`${keyPrefix}_review`] || '未批阅';
                     const annotation = me[`${keyPrefix}_annotation`] || '';
                      
                     mod.rejected = (review === '不通过');
                      mod.annotation = (review === '不通过' && annotation) ? `不通过原因：${annotation}` : '';

                      if (review === '不通过') {
                          mod.filename = fname ? `未通过：${fname}` : '已提交(未通过)';
                          mod.message = '审核未通过，请修改后重新提交';
                          mod.msgClass = 'message error';
                      } else if (review === '通过') {
                          mod.filename = fname ? `已通过：${fname}` : '已提交(通过)';
                          mod.message = '审核通过';
                          mod.msgClass = 'message success';
                      } else {
                          mod.filename = fname ? `已提交：${fname}` : '已提交文件';
                          mod.message = '已提交，可重新上传替换原文件';
                          mod.msgClass = '';
                      }
 
                      mod.finalTime = me[mod.keyTime] ? `最后提交时间：${String(me[mod.keyTime])}` : '';
                 } else {
                     // Even if not submitted (file deleted/rejected), we might still have review history
                     // If the teacher rejected it, the file path is gone (isSub = false), but review result might persist?
                     // Actually, based on previous fix, we reset review to '未批阅' on NEW UPLOAD.
                     // But if teacher REJECTS (deletes file), we want to show the rejection reason.
                     // The teacher's reject action (api/reject_universal.php) deletes the file path but should KEEP the review result as '不通过'
                     // Wait, reject_universal.php currently might be deleting the path.
                     // Let's check if we have review data even if isSub is false.
                     
                     const keyPrefix = mod.fileType;
                     const review = me[`${keyPrefix}_review`];
                     const annotation = me[`${keyPrefix}_annotation`];
                     
                     if (review === '不通过') {
                         mod.rejected = true;
                         mod.annotation = annotation ? `不通过原因：${annotation}` : '';
                         mod.filename = '已打回';
                         mod.message = '审核未通过，请重新提交';
                         mod.msgClass = 'message error';
                         // We set submitted to false effectively, but we want to show the error state.
                         // The UI depends on mod.filename to show the chip.
                     } else {
                         mod.filename = '';
                         mod.message = '仅允许提交一个文件';
                         mod.msgClass = '';
                         mod.finalTime = '';
                         mod.rejected = false;
                         mod.annotation = '';
                     }
                 }
             });
         }
       } catch (e) {
           console.error(e);
       }
    };

    return { modules, handleFileSelect, triggerUpload, handleDrop, submitFile, loadStatus, currentUser };
  }
});

async function uploadGenericChunked(apiPath, file, username, replace, fileType, onProgress) {
  const total = Math.ceil(file.size / CHUNK_SIZE) || 1;
  const uploadId = `${Date.now()}-${Math.random().toString(36).slice(2,10)}`;
  for (let i = 0; i < total; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(file.size, start + CHUNK_SIZE);
    const blob = file.slice(start, end);
    const fd = new FormData();
    fd.append('username', username);
    fd.append('studentID', username);
    fd.append('filename', file.name);
    fd.append('upload_id', uploadId);
    fd.append('chunk_index', String(i));
    fd.append('total_chunks', String(total));
    fd.append('replace', replace ? '1' : '0');
    if (fileType) fd.append('file_type', fileType);
    fd.append('chunk', blob, `${file.name}.part${i}`);
    
    const res = await fetch(apiPath, { method: 'POST', credentials: 'include', body: fd });
    if (!res.ok) return false;
    if (onProgress) onProgress((i + 1) / total);
  }
  return true;
}

function initGraduationSection(user) {
    if (!gradAppInstance) {
        gradAppInstance = gradApp.mount('#grad-app');
    }
    if (gradAppInstance) {
        gradAppInstance.currentUser = user;
        gradAppInstance.loadStatus();
    }
}
