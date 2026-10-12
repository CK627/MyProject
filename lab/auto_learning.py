# -*- coding: utf-8 -*-
"""自主学习引擎：题目搜索 → 生成 → 执行 → 分析 → 数据收集 → 训练 闭环

核心流程：
1. 题目来源：网络资源搜索 + SSH 自动生成（ck-win）
2. 题目管理：每道题一个独立子文件夹
3. 执行分析：ctfsweep 实际扫描，分析输出
4. 数据收集：收集训练数据（候选 + 标签）
5. 迭代改进：判断成功 → 分析改进 → 修复代码 → 重新测试
6. 持续循环：不中断运行，累积经验

运行方式（源码直跑，无外部安装）：
    cd <项目根> && python3 lab/auto_learning.py [--loop] [--config F]

数据布局：数据集/进度等运行时数据放 ~/.devtools/ctfsweep/auto_learn/（缓存）；
训练出的模型统一写回项目 models/model.ctfj（随项目版本管理）。
"""

import json
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- 配置
DEFAULT_CONFIG = {
    # SSH 配置
    "ssh_host": "ck-win",
    "ssh_user": "student",
    "ssh_base_dir": "C:/Users/student/Desktop/CTFLearn",
    
    # 题目生成配置
    "max_tasks": 50,  # 最大生成题目数
    "task_types": ["pcap", "evtx", "registry", "memory", "file_forensics"],
    
    # 执行配置
    "ctfsweep_path": None,  # 自动检测
    "min_score_threshold": 0.6,  # 置信度阈值
    
    # 迭代配置
    "max_iterations": 10,  # 最大迭代次数
    "improve_threshold": 0.7,  # 改进阈值（成功率）
    
    # 数据收集（统一放 devtools 用户数据目录）
    "data_dir": "~/.devtools/ctfsweep/auto_learn",
    "dataset_path": None,  # 自动生成
}


class AutoLearningEngine:
    """自主学习引擎核心类"""
    
    def __init__(self, config=None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.data_dir = Path(self.config["data_dir"]).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据集路径
        if not self.config["dataset_path"]:
            self.config["dataset_path"] = str(self.data_dir / "dataset.jsonl")
        
        # 统计信息
        self.stats = {
            "tasks_generated": 0,
            "tasks_executed": 0,
            "tasks_successful": 0,
            "data_points_collected": 0,
            "iterations": 0,
            "code_improvements": 0,
            "start_time": None,
        }
        
        # 确保数据集文件存在
        if not Path(self.config["dataset_path"]).exists():
            Path(self.config["dataset_path"]).touch()
    
    def run(self, loop=True):
        """启动自主学习循环"""
        self.stats["start_time"] = datetime.now().isoformat()
        print("=" * 60)
        print("CTFSWEEP 自主学习引擎启动")
        print("=" * 60)
        print(f"数据目录: {self.data_dir}")
        print(f"数据集: {self.config['dataset_path']}")
        print(f"最大题目数: {self.config['max_tasks']}")
        print(f"最大迭代次数: {self.config['max_iterations']}")
        print("=" * 60)
        
        iteration = 0
        while True:
            iteration += 1
            self.stats["iterations"] = iteration
            
            # 检查是否达到上限
            if iteration > self.config["max_iterations"]:
                print("\n[INFO] 达到最大迭代次数，结束学习")
                break
            
            print(f"\n{'=' * 60}")
            print(f"第 {iteration} 轮学习")
            print(f"{'=' * 60}")
            
            # 1. 生成题目
            self._generate_tasks()
            
            # 2. 执行扫描
            self._execute_tasks()
            
            # 3. 分析结果
            success_rate = self._analyze_results()
            print(f"\n[STATS] 当前成功率: {success_rate:.2%}")
            
            # 4. 收集数据
            self._collect_training_data()
            
            # 5. 训练模型
            self._train_model()
            
            # 6. 迭代改进（如果需要）
            if success_rate < self.config["improve_threshold"] and iteration < self.config["max_iterations"]:
                self._improve_code()
            
            # 7. 保存进度
            self._save_progress()
            
            # 如果不是循环模式，退出
            if not loop:
                break
            
            # 等待一段时间（模拟人类学习节奏）
            print(f"\n[INFO] 等待 5 秒后继续下一轮...")
            time.sleep(5)
    
    def _generate_tasks(self):
        """生成 CTF 取证题目"""
        print("\n[1/6] 生成题目...")
        
        # 从 SSH 远程生成
        try:
            from .task_generator import TaskGenerator      # 包内运行
        except ImportError:
            from task_generator import TaskGenerator       # lab/ 目录直跑
        generator = TaskGenerator(self.config)
        new_tasks = generator.generate_tasks()
        self.stats["tasks_generated"] += len(new_tasks)
        print(f"  ✓ 生成 {len(new_tasks)} 道新题目")
        
        # 也可以从网络搜索获取（预留接口）
        # self._search_online_tasks()
    
    def _execute_tasks(self):
        """执行题目扫描"""
        print("\n[2/6] 执行扫描...")
        
        task_dir = Path(self.config["ssh_base_dir"]).expanduser()
        if not task_dir.exists():
            print(f"  [WARN] 题目目录不存在: {task_dir}")
            return
        
        task_folders = [f for f in task_dir.iterdir() if f.is_dir()]
        print(f"  找到 {len(task_folders)} 道题目")
        
        executed = 0
        for task_folder in task_folders:
            # 检查是否已执行
            result_file = task_folder / "result.json"
            if result_file.exists():
                continue
            
            # 执行扫描
            success = self._scan_task(task_folder)
            if success:
                executed += 1
                self.stats["tasks_executed"] += 1
        
        print(f"  ✓ 执行扫描 {executed} 道题目")
    
    def _scan_task(self, task_folder):
        """扫描单个题目"""
        try:
            # 查找题目文件
            files = list(task_folder.glob("*.pcap*")) + list(task_folder.glob("*.evtx")) + list(task_folder.glob("*.reg"))
            if not files:
                return False
            
            # 构建 ctfsweep 命令
            ctfsweep_path = self.config.get("ctfsweep_path", "ctfsweep")
            cmd = [
                ctfsweep_path,
                str(files[0]),
                "--judge",
                "--min-score", "0",
                "--limit", "50",
            ]
            
            # 执行扫描
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # 保存结果
            result_data = {
                "task": str(task_folder.name),
                "file": str(files[0]),
                "exit_code": result.returncode,
                "output": result.stdout[:5000],  # 限制输出长度
                "timestamp": datetime.now().isoformat(),
            }
            
            result_file = task_folder / "result.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"  [ERROR] 扫描 {task_folder.name} 失败: {e}")
            return False
    
    def _analyze_results(self):
        """分析扫描结果"""
        print("\n[3/6] 分析结果...")
        
        task_dir = Path(self.config["ssh_base_dir"]).expanduser()
        if not task_dir.exists():
            return 0.0
        
        task_folders = [f for f in task_dir.iterdir() if f.is_dir()]
        results = [f / "result.json" for f in task_folders if (f / "result.json").exists()]
        
        if not results:
            return 0.0
        
        # 分析成功率
        successful = 0
        for result_file in results:
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    result = json.load(f)
                
                # 判断是否成功（简化：检查输出中是否有 flag）
                output = result.get("output", "")
                has_flag = "flag{" in output.lower() or "ctf{" in output.lower()
                
                if has_flag:
                    successful += 1
                    self.stats["tasks_successful"] += 1
                
            except Exception:
                pass
        
        success_rate = successful / len(results) if results else 0.0
        print(f"  ✓ 分析完成: {successful}/{len(results)} 成功 ({success_rate:.2%})")
        
        return success_rate
    
    def _collect_training_data(self):
        """收集训练数据"""
        print("\n[4/6] 收集训练数据...")
        
        task_dir = Path(self.config["ssh_base_dir"]).expanduser()
        if not task_dir.exists():
            return
        
        task_folders = [f for f in task_dir.iterdir() if f.is_dir()]
        data_points = 0
        
        for task_folder in task_folders:
            result_file = task_folder / "result.json"
            if not result_file.exists():
                continue
            
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    result = json.load(f)
                
                output = result.get("output", "")
                
                # 从输出中提取候选
                lines = output.split("\n")
                for line in lines:
                    if "flag{" in line.lower() or "ctf{" in line.lower():
                        # 构建训练样本
                        sample = {
                            "val": line.strip(),
                            "kind": "明文flag" if "flag{" in line.lower() else "关键词",
                            "score": 0.95 if "flag{" in line.lower() else 0.6,
                            "label": 1.0,  # 真阳性
                            "source": str(task_folder.name),
                            "timestamp": datetime.now().isoformat(),
                        }
                        
                        # 追加到数据集
                        with open(self.config["dataset_path"], "a", encoding="utf-8") as df:
                            df.write(json.dumps(sample, ensure_ascii=False) + "\n")
                        
                        data_points += 1
            
            except Exception:
                pass
        
        self.stats["data_points_collected"] += data_points
        print(f"  ✓ 收集 {data_points} 条训练数据")
    
    def _train_model(self):
        """训练模型"""
        print("\n[5/6] 训练模型...")
        
        dataset_path = self.config["dataset_path"]
        if not Path(dataset_path).exists():
            print("  [WARN] 数据集不存在，跳过训练")
            return
        
        try:
            # 使用 judge 模块训练（模型统一输出到项目 models/）
            import sys as _sys
            _root = str(Path(__file__).resolve().parent.parent)
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            from ctfsweep.core import judge
            
            # 加载数据
            rows = []
            with open(dataset_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        sample = json.loads(line)
                        rows.append(sample)
                    except json.JSONDecodeError:
                        continue
            
            if len(rows) < 8:
                print(f"  [WARN] 数据太少（{len(rows)} 条），跳过训练")
                return
            
            # 训练
            print(f"  使用 {len(rows)} 条数据进行训练")
            model_path = Path(judge.models_dir()) / "model.ctfj"   # 模型回归项目 models/
            model_path.parent.mkdir(parents=True, exist_ok=True)
            judge.run_training(rows, model_out=str(model_path), epochs=250)
            print(f"  ✓ 模型训练完成，保存至: {model_path}")
            
        except Exception as e:
            print(f"  [ERROR] 训练失败: {e}")
    
    def _improve_code(self):
        """迭代改进代码"""
        print("\n[6/6] 代码改进...")
        
        # 分析当前模型性能
        success_rate = self.stats["tasks_successful"] / max(1, self.stats["tasks_executed"])
        
        if success_rate >= self.config["improve_threshold"]:
            print(f"  ✓ 成功率 {success_rate:.2%} 已达标，无需改进")
            return
        
        # 这里可以实现自动化代码改进逻辑
        # 例如：分析失败案例，提取特征，调整特征权重等
        print(f"  [INFO] 成功率 {success_rate:.2%} 低于阈值 {self.config['improve_threshold']:.2%}")
        print(f"  [INFO] 当前为手动改进模式，请查看分析报告")
        
        # 生成分析报告
        report_path = self.data_dir / f"improvement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 代码改进分析报告\n\n")
            f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
            f.write(f"当前成功率: {success_rate:.2%}\n")
            f.write(f"目标阈值: {self.config['improve_threshold']:.2%}\n\n")
            f.write("## 改进建议\n\n")
            f.write("1. 检查特征提取逻辑，是否有遗漏的语义特征\n")
            f.write("2. 分析失败案例，找出共同特征\n")
            f.write("3. 调整模型架构，增加隐层节点\n")
            f.write("4. 增加更多训练数据\n")
        
        print(f"  ✓ 分析报告已保存: {report_path}")
        self.stats["code_improvements"] += 1
    
    def _save_progress(self):
        """保存学习进度"""
        progress = {
            "stats": self.stats,
            "timestamp": datetime.now().isoformat(),
        }
        
        progress_path = self.data_dir / "progress.json"
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        
        print(f"\n[INFO] 进度已保存至: {progress_path}")
    
    def get_report(self):
        """生成学习报告"""
        report = {
            "title": "CTFSWEEP 自主学习报告",
            "stats": self.stats,
            "timestamp": datetime.now().isoformat(),
        }
        return report


# ---------------------------------------------------------------- CLI 入口
def cmd_auto_learn(args):
    """ctfsweep auto-learn: 启动自主学习闭环"""
    import argparse
    
    parser = argparse.ArgumentParser(description="启动自主学习闭环")
    parser.add_argument("--config", help="配置文件路径（JSON）")
    parser.add_argument("--max-tasks", type=int, help="最大生成题目数")
    parser.add_argument("--max-iterations", type=int, help="最大迭代次数")
    parser.add_argument("--loop", action="store_true", default=True, help="持续循环学习")
    parser.add_argument("--no-loop", action="store_true", help="单次运行，不循环")
    parser.add_argument("--report", action="store_true", help="生成学习报告")
    
    parsed = parser.parse_args(args)
    
    # 加载配置
    config = DEFAULT_CONFIG.copy()
    if parsed.config and Path(parsed.config).exists():
        with open(parsed.config, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    
    # 覆盖命令行参数
    if parsed.max_tasks:
        config["max_tasks"] = parsed.max_tasks
    if parsed.max_iterations:
        config["max_iterations"] = parsed.max_iterations
    
    # 创建引擎并运行
    engine = AutoLearningEngine(config)
    
    if parsed.report:
        engine.run(loop=False)
        report = engine.get_report()
        print("\n" + "=" * 60)
        print("学习报告")
        print("=" * 60)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        engine.run(loop=not parsed.no_loop)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd_auto_learn(sys.argv[1:])
    else:
        engine = AutoLearningEngine()
        engine.run()
