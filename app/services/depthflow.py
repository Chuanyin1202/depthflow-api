import logging
import os
from typing import Dict, Any, Optional
import subprocess
import asyncio
import json
from PIL import Image
import numpy as np
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class DepthFlowService:
    """DepthFlow 整合服務"""
    
    def __init__(self):
        self.max_resolution = settings.depthflow_max_resolution
        self.default_fps = settings.depthflow_default_fps
        self.default_duration = settings.depthflow_default_duration
        
    async def process_image(
        self, 
        input_path: str, 
        output_path: str,
        parameters: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> bool:
        """
        使用 DepthFlow 處理圖片
        
        Args:
            input_path: 輸入圖片路徑
            output_path: 輸出檔案路徑
            parameters: 處理參數
            progress_callback: 進度回調函數
            
        Returns:
            bool: 是否成功
        """
        try:
            # 使用 DepthFlow 的 Python API
            try:
                from depthflow.scene import DepthScene
                from depthflow.animation import Animation
                
                # 更新進度
                if progress_callback:
                    await progress_callback(10, "初始化 DepthFlow")
                
                # 建立 DepthScene 實例 (無頭模式)
                scene = DepthScene(backend="headless")
                
                # 設定輸入圖片
                scene.input(image=[input_path])
                
                # 更新進度
                if progress_callback:
                    await progress_callback(30, "載入圖片完成")
                
                # 配置動畫參數
                scene.config.animation.clear()  # 清除預設動畫
                
                # 根據參數設定動畫類型
                camera_movement = parameters.get('camera_movement', 'orbit')
                depth_strength = parameters.get('depth_strength', 1.0)
                
                if camera_movement == 'orbit':
                    # 使用軌道動畫
                    scene.config.animation.add(Animation.Orbital(intensity=depth_strength))
                elif camera_movement == 'zoom':
                    # 使用縮放動畫
                    scene.config.animation.add(Animation.Zoom(
                        intensity=depth_strength * 0.3,
                        loop=True
                    ))
                elif camera_movement == 'dolly':
                    # 使用推軌動畫
                    scene.config.animation.add(Animation.Dolly(
                        intensity=depth_strength * 0.5
                    ))
                else:
                    # 預設使用軌道動畫
                    scene.config.animation.add(Animation.Orbital(intensity=depth_strength))
                
                # 更新進度
                if progress_callback:
                    await progress_callback(50, "配置動畫參數完成")
                
                # 設定輸出參數
                fps = parameters.get('fps', self.default_fps)
                duration = parameters.get('animation_duration', self.default_duration)
                resolution = parameters.get('resolution')
                
                if resolution:
                    scene.ssaa = 1.5  # 超採樣抗鋸齒
                
                # 設定編碼器
                output_format = parameters.get('output_format', 'mp4')
                if output_format == 'mp4':
                    scene.ffmpeg.h264(preset="fast")
                elif output_format == 'webm':
                    scene.ffmpeg.vp9()
                
                # 更新進度
                if progress_callback:
                    await progress_callback(70, "開始渲染動畫")
                
                # 執行渲染
                scene.main(
                    output=output_path,
                    time=duration,
                    fps=fps,
                    turbo=False  # 高品質模式
                )
                
                # 更新進度
                if progress_callback:
                    await progress_callback(90, "動畫生成完成")
                
                return True
                
            except ImportError as e:
                logger.warning(f"無法導入 DepthFlow Python API: {e}")
                # 降級到使用 CLI
                return await self._process_with_cli(input_path, output_path, parameters, progress_callback)
                
        except Exception as e:
            logger.error(f"DepthFlow 處理失敗: {e}")
            return False
    
    async def _process_with_cli(
        self, 
        input_path: str, 
        output_path: str, 
        parameters: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> bool:
        """
        使用 CLI 處理圖片（降級方案）
        """
        try:
            # 更新進度
            if progress_callback:
                await progress_callback(20, "使用 CLI 模式處理")
            
            # 構建基本命令
            cmd = [
                "depthflow",
                "--image", input_path,
                "--output", output_path,
                "--backend", "headless",  # 無頭模式
                "--time", str(parameters.get('animation_duration', self.default_duration)),
                "--fps", str(parameters.get('fps', self.default_fps)),
            ]
            
            # 設定解析度
            resolution = parameters.get('resolution')
            if resolution:
                cmd.extend(["--ssaa", "1.5"])
            
            # 添加動畫類型（基於之前的範例代碼）
            camera_movement = parameters.get('camera_movement', 'orbit')
            depth_strength = parameters.get('depth_strength', 1.0)
            
            # 根據 DepthFlow 的實際 CLI 格式添加動畫參數
            if camera_movement == 'orbit':
                cmd.extend(["circle", "--intensity", str(depth_strength)])
            elif camera_movement == 'zoom':
                cmd.extend(["zoom", "--intensity", str(depth_strength * 0.3), "--loop"])
            elif camera_movement == 'dolly':
                cmd.extend(["dolly", "--intensity", str(depth_strength * 0.5)])
            else:
                cmd.extend(["circle", "--intensity", str(depth_strength)])
            
            # 更新進度
            if progress_callback:
                await progress_callback(50, "執行 DepthFlow CLI")
            
            # 執行命令
            logger.info(f"執行命令: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # 記錄詳細輸出
            if stdout:
                logger.info(f"CLI stdout: {stdout.decode()}")
            if stderr:
                logger.warning(f"CLI stderr: {stderr.decode()}")
            
            if process.returncode != 0:
                logger.error(f"DepthFlow CLI 執行失敗 (返回碼: {process.returncode})")
                logger.error(f"錯誤輸出: {stderr.decode()}")
                return False
            
            # 更新進度
            if progress_callback:
                await progress_callback(90, "CLI 處理完成")
            
            # 檢查輸出檔案是否存在
            if os.path.exists(output_path):
                logger.info(f"輸出檔案已生成: {output_path}")
                return True
            else:
                logger.error(f"輸出檔案未生成: {output_path}")
                return False
            
        except Exception as e:
            logger.error(f"CLI 處理失敗: {e}")
            return False
    
    def check_depthflow_available(self) -> Dict[str, bool]:
        """檢查 DepthFlow 是否可用"""
        result = {
            "python_api": False,
            "cli": False,
            "overall": False,
            "python_error": None,
            "cli_error": None
        }
        
        # 檢查 Python API
        try:
            import depthflow
            result["python_api"] = True
            logger.info(f"DepthFlow Python API 可用")
        except ImportError as e:
            result["python_error"] = str(e)
            logger.warning(f"DepthFlow Python API 不可用: {e}")
        
        # 檢查 CLI
        try:
            process = subprocess.run(
                ["depthflow", "--version"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            result["cli"] = process.returncode == 0
            if result["cli"]:
                logger.info(f"DepthFlow CLI 可用: {process.stdout.strip()}")
            else:
                result["cli_error"] = process.stderr.strip()
                logger.warning(f"DepthFlow CLI 失敗: {process.stderr.strip()}")
        except subprocess.TimeoutExpired:
            result["cli_error"] = "CLI 執行超時"
            logger.warning("DepthFlow CLI 執行超時")
        except Exception as e:
            result["cli_error"] = str(e)
            logger.warning(f"DepthFlow CLI 執行錯誤: {e}")
        
        result["overall"] = result["python_api"] or result["cli"]
        return result
    
    async def estimate_processing_time(self, parameters: Dict[str, Any]) -> float:
        """
        估算處理時間（秒）
        
        Args:
            parameters: 處理參數
            
        Returns:
            float: 估計的處理時間
        """
        # 基礎時間（秒）
        base_time = 10.0
        
        # 根據動畫時長調整
        duration = parameters.get('animation_duration', self.default_duration)
        time_factor = duration / 3.0  # 3秒為基準
        
        # 根據 FPS 調整
        fps = parameters.get('fps', self.default_fps)
        fps_factor = fps / 30.0  # 30fps 為基準
        
        # 根據解析度調整
        resolution = parameters.get('resolution', 1080)
        resolution_factor = (resolution / 1080) ** 2  # 平方關係
        
        # 計算總時間
        estimated_time = base_time * time_factor * fps_factor * resolution_factor
        
        # 加入一些緩衝
        return estimated_time * 1.5