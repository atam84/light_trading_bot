# src/api_clients/quickchart.py

from typing import Dict, Any, Optional, List, Union, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import base64
import json

from .base_client import BaseHTTPClient, APIResponse
from .ccxt_gateway import MarketData
from ..utils.exceptions import ChartError, APIError
from ..config.settings import get_config

logger = logging.getLogger(__name__)

@dataclass
class ChartConfig:
    """Chart configuration container"""
    chart_type: str
    width: int = 800
    height: int = 400
    title: Optional[str] = None
    background_color: str = 'white'
    format: str = 'png'  # png, jpg, svg, pdf
    
@dataclass
class CandlestickPoint:
    """Candlestick data point"""
    x: Union[str, int]  # timestamp or date string
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None

@dataclass
class LinePoint:
    """Line chart data point"""
    x: Union[str, int]
    y: float
    label: Optional[str] = None

@dataclass
class TradeMarker:
    """Trade marker for charts"""
    x: Union[str, int]
    y: float
    type: str  # 'buy', 'sell'
    amount: Optional[float] = None
    price: Optional[float] = None

class QuickChartClient(BaseHTTPClient):
    """Client for QuickChart API integration"""
    
    def __init__(self, base_url: Optional[str] = None, **kwargs):
        config = get_config()
        if base_url is None:
            base_url = config.get('api.quickchart_url', 'http://quickchart:8080')
        
        super().__init__(
            base_url=base_url,
            timeout=config.get('api.timeout', 30),
            max_retries=config.get('api.max_retries', 3),
            headers={'Content-Type': 'application/json'},
            **kwargs
        )
        
        # Chart color schemes
        self.color_schemes = {
            'default': {
                'candlestick_up': '#26a69a',
                'candlestick_down': '#ef5350',
                'volume': '#90a4ae',
                'buy_marker': '#4caf50',
                'sell_marker': '#f44336',
                'line_primary': '#2196f3',
                'line_secondary': '#ff9800',
                'background': 'white',
                'text': '#333333'
            },
            'dark': {
                'candlestick_up': '#00e676',
                'candlestick_down': '#ff5722',
                'volume': '#607d8b',
                'buy_marker': '#4caf50',
                'sell_marker': '#f44336',
                'line_primary': '#03dac6',
                'line_secondary': '#ffc107',
                'background': '#121212',
                'text': '#ffffff'
            }
        }
    
    def _convert_market_data_to_candlestick(self, market_data: List[MarketData]) -> List[CandlestickPoint]:
        """Convert MarketData objects to candlestick points"""
        points = []
        for data in market_data:
            # Use timestamp or create date string
            x_value = data.datetime_str if data.datetime_str else data.timestamp
            points.append(CandlestickPoint(
                x=x_value,
                open=data.open,
                high=data.high,
                low=data.low,
                close=data.close,
                volume=data.volume
            ))
        return points
    
    def _create_candlestick_chart_config(
        self,
        data: List[CandlestickPoint],
        config: ChartConfig,
        color_scheme: str = 'default',
        show_volume: bool = True
    ) -> Dict[str, Any]:
        """Create candlestick chart configuration"""
        colors = self.color_schemes.get(color_scheme, self.color_schemes['default'])
        
        # Prepare candlestick data
        candlestick_data = []
        volume_data = []
        
        for point in data:
            candlestick_data.append({
                'x': point.x,
                'o': point.open,
                'h': point.high,
                'l': point.low,
                'c': point.close
            })
            
            if show_volume and point.volume is not None:
                volume_data.append({
                    'x': point.x,
                    'y': point.volume
                })
        
        datasets = [{
            'label': 'Price',
            'data': candlestick_data,
            'type': 'candlestick',
            'color': {
                'up': colors['candlestick_up'],
                'down': colors['candlestick_down'],
                'unchanged': colors['candlestick_up']
            }
        }]
        
        # Add volume dataset if requested
        if show_volume and volume_data:
            datasets.append({
                'label': 'Volume',
                'data': volume_data,
                'type': 'bar',
                'backgroundColor': colors['volume'],
                'yAxisID': 'volume'
            })
        
        scales = {
            'x': {
                'type': 'time' if isinstance(data[0].x, int) else 'category',
                'display': True
            },
            'y': {
                'type': 'linear',
                'display': True,
                'position': 'left'
            }
        }
        
        # Add volume scale if showing volume
        if show_volume and volume_data:
            scales['volume'] = {
                'type': 'linear',
                'display': True,
                'position': 'right',
                'grid': {
                    'drawOnChartArea': False
                }
            }
        
        chart_config = {
            'type': 'candlestick',
            'data': {
                'datasets': datasets
            },
            'options': {
                'responsive': True,
                'scales': scales,
                'plugins': {
                    'legend': {
                        'display': True
                    }
                }
            }
        }
        
        if config.title:
            chart_config['options']['plugins']['title'] = {
                'display': True,
                'text': config.title
            }
        
        return chart_config
    
    def _create_line_chart_config(
        self,
        datasets: List[Dict[str, Any]],
        config: ChartConfig,
        color_scheme: str = 'default'
    ) -> Dict[str, Any]:
        """Create line chart configuration"""
        colors = self.color_schemes.get(color_scheme, self.color_schemes['default'])
        
        # Apply default colors to datasets
        color_list = [colors['line_primary'], colors['line_secondary']]
        for i, dataset in enumerate(datasets):
            if 'borderColor' not in dataset:
                dataset['borderColor'] = color_list[i % len(color_list)]
            if 'backgroundColor' not in dataset:
                dataset['backgroundColor'] = dataset['borderColor'] + '20'  # Add transparency
        
        chart_config = {
            'type': 'line',
            'data': {
                'datasets': datasets
            },
            'options': {
                'responsive': True,
                'scales': {
                    'x': {
                        'type': 'time' if any(isinstance(point.get('x'), int) for dataset in datasets for point in dataset.get('data', [])) else 'category',
                        'display': True
                    },
                    'y': {
                        'type': 'linear',
                        'display': True
                    }
                },
                'plugins': {
                    'legend': {
                        'display': True
                    }
                }
            }
        }
        
        if config.title:
            chart_config['options']['plugins']['title'] = {
                'display': True,
                'text': config.title
            }
        
        return chart_config
    
    def _add_trade_markers_to_config(
        self,
        chart_config: Dict[str, Any],
        trade_markers: List[TradeMarker],
        color_scheme: str = 'default'
    ) -> Dict[str, Any]:
        """Add trade markers to existing chart configuration"""
        colors = self.color_schemes.get(color_scheme, self.color_schemes['default'])
        
        buy_markers = []
        sell_markers = []
        
        for marker in trade_markers:
            marker_data = {'x': marker.x, 'y': marker.y}
            if marker.type.lower() == 'buy':
                buy_markers.append(marker_data)
            elif marker.type.lower() == 'sell':
                sell_markers.append(marker_data)
        
        # Add buy markers
        if buy_markers:
            chart_config['data']['datasets'].append({
                'label': 'Buy Signals',
                'data': buy_markers,
                'type': 'scatter',
                'backgroundColor': colors['buy_marker'],
                'borderColor': colors['buy_marker'],
                'pointStyle': 'triangle',
                'pointRadius': 8,
                'showLine': False
            })
        
        # Add sell markers
        if sell_markers:
            chart_config['data']['datasets'].append({
                'label': 'Sell Signals',
                'data': sell_markers,
                'type': 'scatter',
                'backgroundColor': colors['sell_marker'],
                'borderColor': colors['sell_marker'],
                'pointStyle': 'triangle',
                'pointRadius': 8,
                'rotation': 180,  # Flip triangle for sell
                'showLine': False
            })
        
        return chart_config
    
    async def create_candlestick_chart(
        self,
        market_data: List[MarketData],
        config: Optional[ChartConfig] = None,
        trade_markers: Optional[List[TradeMarker]] = None,
        color_scheme: str = 'default',
        show_volume: bool = True
    ) -> bytes:
        """
        Create candlestick chart from market data
        
        Args:
            market_data: List of MarketData objects
            config: Chart configuration
            trade_markers: Optional trade markers to overlay
            color_scheme: Color scheme ('default' or 'dark')
            show_volume: Whether to show volume bars
        
        Returns:
            Chart image as bytes
        """
        if not market_data:
            raise ValueError("Market data cannot be empty")
        
        if config is None:
            config = ChartConfig(chart_type='candlestick')
        
        try:
            # Convert market data to candlestick points
            candlestick_data = self._convert_market_data_to_candlestick(market_data)
            
            # Create chart configuration
            chart_config = self._create_candlestick_chart_config(
                candlestick_data, config, color_scheme, show_volume
            )
            
            # Add trade markers if provided
            if trade_markers:
                chart_config = self._add_trade_markers_to_config(
                    chart_config, trade_markers, color_scheme
                )
            
            # Create request payload
            payload = {
                'chart': chart_config,
                'width': config.width,
                'height': config.height,
                'backgroundColor': self.color_schemes[color_scheme]['background'],
                'format': config.format
            }
            
            response = await self.post('/chart', data=payload)
            
            if not response.is_success:
                raise APIError(f"Failed to create chart: {response.error_message}")
            
            # Response should be image bytes
            if isinstance(response.data, str):
                # If response is base64 encoded
                try:
                    return base64.b64decode(response.data)
                except:
                    # If response is raw bytes as string
                    return response.data.encode()
            elif isinstance(response.data, bytes):
                return response.data
            else:
                raise ChartError(f"Unexpected chart response format: {type(response.data)}")
                
        except Exception as e:
            logger.error(f"Error creating candlestick chart: {str(e)}")
            raise ChartError(f"Failed to create candlestick chart: {str(e)}")
    
    async def create_price_line_chart(
        self,
        price_data: List[LinePoint],
        config: Optional[ChartConfig] = None,
        additional_lines: Optional[Dict[str, List[LinePoint]]] = None,
        trade_markers: Optional[List[TradeMarker]] = None,
        color_scheme: str = 'default'
    ) -> bytes:
        """
        Create line chart for price data
        
        Args:
            price_data: Main price line data
            config: Chart configuration
            additional_lines: Additional lines to plot (e.g., moving averages)
            trade_markers: Optional trade markers to overlay
            color_scheme: Color scheme ('default' or 'dark')
        
        Returns:
            Chart image as bytes
        """
        if not price_data:
            raise ValueError("Price data cannot be empty")
        
        if config is None:
            config = ChartConfig(chart_type='line')
        
        try:
            # Prepare datasets
            datasets = [{
                'label': 'Price',
                'data': [{'x': point.x, 'y': point.y} for point in price_data],
                'fill': False,
                'tension': 0.1
            }]
            
            # Add additional lines
            if additional_lines:
                for label, line_data in additional_lines.items():
                    datasets.append({
                        'label': label,
                        'data': [{'x': point.x, 'y': point.y} for point in line_data],
                        'fill': False,
                        'tension': 0.1
                    })
            
            # Create chart configuration
            chart_config = self._create_line_chart_config(datasets, config, color_scheme)
            
            # Add trade markers if provided
            if trade_markers:
                chart_config = self._add_trade_markers_to_config(
                    chart_config, trade_markers, color_scheme
                )
            
            # Create request payload
            payload = {
                'chart': chart_config,
                'width': config.width,
                'height': config.height,
                'backgroundColor': self.color_schemes[color_scheme]['background'],
                'format': config.format
            }
            
            response = await self.post('/chart', data=payload)
            
            if not response.is_success:
                raise APIError(f"Failed to create chart: {response.error_message}")
            
            # Handle response
            if isinstance(response.data, str):
                try:
                    return base64.b64decode(response.data)
                except:
                    return response.data.encode()
            elif isinstance(response.data, bytes):
                return response.data
            else:
                raise ChartError(f"Unexpected chart response format: {type(response.data)}")
                
        except Exception as e:
            logger.error(f"Error creating price line chart: {str(e)}")
            raise ChartError(f"Failed to create price line chart: {str(e)}")
    
    async def create_performance_chart(
        self,
        portfolio_values: List[LinePoint],
        benchmark_values: Optional[List[LinePoint]] = None,
        config: Optional[ChartConfig] = None,
        color_scheme: str = 'default'
    ) -> bytes:
        """
        Create performance comparison chart
        
        Args:
            portfolio_values: Portfolio value over time
            benchmark_values: Benchmark values for comparison (optional)
            config: Chart configuration
            color_scheme: Color scheme ('default' or 'dark')
        
        Returns:
            Chart image as bytes
        """
        if not portfolio_values:
            raise ValueError("Portfolio values cannot be empty")
        
        if config is None:
            config = ChartConfig(
                chart_type='line',
                title='Portfolio Performance'
            )
        
        try:
            datasets = [{
                'label': 'Portfolio',
                'data': [{'x': point.x, 'y': point.y} for point in portfolio_values],
                'fill': False,
                'tension': 0.1
            }]
            
            if benchmark_values:
                datasets.append({
                    'label': 'Benchmark',
                    'data': [{'x': point.x, 'y': point.y} for point in benchmark_values],
                    'fill': False,
                    'tension': 0.1
                })
            
            # Create chart configuration
            chart_config = self._create_line_chart_config(datasets, config, color_scheme)
            
            # Customize for performance chart
            chart_config['options']['scales']['y']['title'] = {
                'display': True,
                'text': 'Value ($)'
            }
            chart_config['options']['scales']['x']['title'] = {
                'display': True,
                'text': 'Time'
            }
            
            # Create request payload
            payload = {
                'chart': chart_config,
                'width': config.width,
                'height': config.height,
                'backgroundColor': self.color_schemes[color_scheme]['background'],
                'format': config.format
            }
            
            response = await self.post('/chart', data=payload)
            
            if not response.is_success:
                raise APIError(f"Failed to create chart: {response.error_message}")
            
            # Handle response
            if isinstance(response.data, str):
                try:
                    return base64.b64decode(response.data)
                except:
                    return response.data.encode()
            elif isinstance(response.data, bytes):
                return response.data
            else:
                raise ChartError(f"Unexpected chart response format: {type(response.data)}")
                
        except Exception as e:
            logger.error(f"Error creating performance chart: {str(e)}")
            raise ChartError(f"Failed to create performance chart: {str(e)}")
    
    async def create_custom_chart(
        self,
        chart_config: Dict[str, Any],
        width: int = 800,
        height: int = 400,
        background_color: str = 'white',
        format: str = 'png'
    ) -> bytes:
        """
        Create custom chart from raw Chart.js configuration
        
        Args:
            chart_config: Raw Chart.js configuration
            width: Chart width in pixels
            height: Chart height in pixels
            background_color: Background color
            format: Output format (png, jpg, svg, pdf)
        
        Returns:
            Chart image as bytes
        """
        try:
            payload = {
                'chart': chart_config,
                'width': width,
                'height': height,
                'backgroundColor': background_color,
                'format': format
            }
            
            response = await self.post('/chart', data=payload)
            
            if not response.is_success:
                raise APIError(f"Failed to create chart: {response.error_message}")
            
            # Handle response
            if isinstance(response.data, str):
                try:
                    return base64.b64decode(response.data)
                except:
                    return response.data.encode()
            elif isinstance(response.data, bytes):
                return response.data
            else:
                raise ChartError(f"Unexpected chart response format: {type(response.data)}")
                
        except Exception as e:
            logger.error(f"Error creating custom chart: {str(e)}")
            raise ChartError(f"Failed to create custom chart: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if QuickChart service is healthy and responding
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Create a simple test chart
            test_config = {
                'type': 'line',
                'data': {
                    'labels': ['A', 'B'],
                    'datasets': [{
                        'data': [1, 2]
                    }]
                }
            }
            
            payload = {
                'chart': test_config,
                'width': 100,
                'height': 100
            }
            
            response = await self.post('/chart', data=payload)
            return response.is_success
            
        except Exception as e:
            logger.error(f"QuickChart health check failed: {str(e)}")
            return False
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported chart formats"""
        return ['png', 'jpg', 'svg', 'pdf']
    
    def get_available_color_schemes(self) -> List[str]:
        """Get list of available color schemes"""
        return list(self.color_schemes.keys())
