"""Runtime monitoring injection for system resource awareness."""

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict

import psutil


class RuntimeMonitor:
    """Monitor system resources and process performance."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = time.time()
    
    def _get_disk_io_stat(self, stat_name: str) -> float:
        """Safely get disk I/O statistics, handling None return values."""
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io is not None and hasattr(disk_io, stat_name):
                return getattr(disk_io, stat_name) / 1024 / 1024  # Convert to MB
            return 0.0
        except (AttributeError, OSError):
            return 0.0
        
    def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage."""
        return {
            'cpu': {
                'system_percent': psutil.cpu_percent(interval=0.1),
                'process_percent': self.process.cpu_percent(),
                'count': psutil.cpu_count()
            },
            'memory': {
                'system_percent': psutil.virtual_memory().percent,
                'process_mb': self.process.memory_info().rss / 1024 / 1024,
                'available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024
            },
            'disk': {
                'usage_percent': psutil.disk_usage('/').percent,
                'io_read_mb': self._get_disk_io_stat('read_bytes'),
                'io_write_mb': self._get_disk_io_stat('write_bytes')
            }
        }
    
    def get_process_info(self) -> Dict[str, Any]:
        """Get information about relevant processes."""
        relevant_processes = []
        
        # Look for language servers, IDEs, and dev tools
        target_names = [
            'node', 'python', 'typescript-language-server', 'pyright',
            'ruff-lsp', 'mypy', 'code', 'cursor', 'docker', 'postgres',
            'redis', 'nginx', 'webpack', 'vite', 'pytest', 'jest'
        ]
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if any(target in proc.info['name'].lower() for target in target_names):
                    relevant_processes.append({
                        'name': proc.info['name'],
                        'pid': proc.info['pid'],
                        'cpu': proc.info['cpu_percent'],
                        'memory': proc.info['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        return {
            'relevant_processes': sorted(relevant_processes, key=lambda x: x['cpu'], reverse=True)[:5],
            'total_processes': len(psutil.pids())
        }
    
    async def get_network_status(self) -> Dict[str, Any]:
        """Get network connectivity and latency."""
        import socket
        
        connections = {
            'active_connections': len(psutil.net_connections()),
            'can_reach_github': False,
            'can_reach_pypi': False,
            'can_reach_npm': False
        }
        
        # Quick connectivity checks in parallel
        async def check_connectivity(host: str) -> bool:
            try:
                # Use asyncio to check connectivity asynchronously
                future = asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: socket.create_connection((host, 443), timeout=1).close()
                )
                await asyncio.wait_for(future, timeout=2)
                return True
            except:
                return False
        
        targets = [
            ('github.com', 'can_reach_github'),
            ('pypi.org', 'can_reach_pypi'),
            ('registry.npmjs.org', 'can_reach_npm')
        ]
        
        # Run connectivity checks in parallel
        tasks = [check_connectivity(host) for host, _ in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for (host, key), result in zip(targets, results):
            if isinstance(result, bool) and result:
                connections[key] = True
                
        return connections
    
    def get_file_system_activity(self) -> Dict[str, Any]:
        """Get recent file system activity."""
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
        
        # Find recently modified files
        recent_files = []
        cutoff_time = time.time() - 300  # Last 5 minutes
        
        try:
            for root, _, files in os.walk(project_dir):
                # Skip hidden and cache directories
                if any(part.startswith('.') or part == '__pycache__' for part in root.split(os.sep)):
                    continue
                    
                for file in files[:10]:  # Limit per directory
                    filepath = os.path.join(root, file)
                    try:
                        stat = os.stat(filepath)
                        if stat.st_mtime > cutoff_time:
                            recent_files.append({
                                'path': os.path.relpath(filepath, project_dir),
                                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                'size_kb': stat.st_size / 1024
                            })
                    except:
                        pass
                        
        except:
            pass
            
        return {
            'recently_modified': sorted(recent_files, key=lambda x: x['modified'], reverse=True)[:10]
        }


async def get_runtime_monitoring_injection() -> str:
    """Create runtime monitoring injection."""
    monitor = RuntimeMonitor()
    
    try:
        # Run monitoring tasks in parallel
        resources_task = asyncio.create_task(asyncio.to_thread(monitor.get_system_resources))
        processes_task = asyncio.create_task(asyncio.to_thread(monitor.get_process_info))
        network_task = monitor.get_network_status()
        files_task = asyncio.create_task(asyncio.to_thread(monitor.get_file_system_activity))
        
        resources, processes, network, files = await asyncio.gather(
            resources_task, processes_task, network_task, files_task
        )
        
        # Build injection based on resource status
        injection_parts = []
        
        # Resource warnings
        if resources['cpu']['system_percent'] > 80:
            injection_parts.append(f"⚠️ HIGH CPU: {resources['cpu']['system_percent']}%")
            
        if resources['memory']['system_percent'] > 85:
            injection_parts.append(f"⚠️ HIGH MEMORY: {resources['memory']['system_percent']}%")
            
        if resources['disk']['usage_percent'] > 90:
            injection_parts.append(f"⚠️ LOW DISK: {resources['disk']['usage_percent']}% used")
        
        # Network issues
        network_issues = []
        if not network['can_reach_github']:
            network_issues.append("GitHub")
        if not network['can_reach_pypi']:
            network_issues.append("PyPI")
        if not network['can_reach_npm']:
            network_issues.append("NPM")
            
        if network_issues:
            injection_parts.append(f"⚠️ UNREACHABLE: {', '.join(network_issues)}")
        
        # Heavy processes
        heavy_procs = [p for p in processes['relevant_processes'] if p['cpu'] > 50]
        if heavy_procs:
            injection_parts.append(f"⚠️ HIGH CPU PROCESSES: {', '.join(p['name'] for p in heavy_procs)}")
        
        # Recently modified files
        if files['recently_modified']:
            recent = files['recently_modified'][:3]
            injection_parts.append(f"Recent activity: {', '.join(f['path'] for f in recent)}")
        
        if injection_parts:
            return "<runtime-monitoring>\n" + "\n".join(injection_parts) + "\n</runtime-monitoring>\n"
        else:
            # Return minimal status if everything is normal
            return f"<runtime-monitoring>System resources normal (CPU: {resources['cpu']['system_percent']:.1f}%, MEM: {resources['memory']['system_percent']:.1f}%)</runtime-monitoring>\n"
            
    except Exception as e:
        # Don't let monitoring errors break the hook
        return f"<!-- Runtime monitoring error: {str(e)} -->\n"