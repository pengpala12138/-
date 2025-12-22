from datetime import datetime
from typing import Optional, Dict, Any
import json


class Tourist:
    def __init__(self, tourist_id: str, name: str, id_card: str,
                 phone: Optional[str] = None, reservation_id: Optional[str] = None,
                 entry_time: Optional[datetime] = None, exit_time: Optional[datetime] = None,
                 entry_method: str = 'online'):
        self.tourist_id = tourist_id
        self.name = name
        self.id_card = id_card
        self.phone = phone
        self.reservation_id = reservation_id
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.entry_method = entry_method

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tourist_id': self.tourist_id,
            'name': self.name,
            'id_card': self.id_card,
            'phone': self.phone,
            'reservation_id': self.reservation_id,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'entry_method': self.entry_method
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tourist':
        return cls(
            tourist_id=data['tourist_id'],
            name=data['name'],
            id_card=data['id_card'],
            phone=data.get('phone'),
            reservation_id=data.get('reservation_id'),
            entry_time=datetime.fromisoformat(data['entry_time']) if data.get('entry_time') else None,
            exit_time=datetime.fromisoformat(data['exit_time']) if data.get('exit_time') else None,
            entry_method=data.get('entry_method', 'online')
        )


class Reservation:
    def __init__(self, reservation_id: str, tourist_id: str, reservation_date: datetime,
                 entry_time_slot: str, group_size: int = 1, status: str = 'confirmed',
                 ticket_amount: float = 0.0, payment_status: str = 'pending'):
        self.reservation_id = reservation_id
        self.tourist_id = tourist_id
        self.reservation_date = reservation_date
        self.entry_time_slot = entry_time_slot
        self.group_size = group_size
        self.status = status
        self.ticket_amount = ticket_amount
        self.payment_status = payment_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            'reservation_id': self.reservation_id,
            'tourist_id': self.tourist_id,
            'reservation_date': self.reservation_date.isoformat() if self.reservation_date else None,
            'entry_time_slot': self.entry_time_slot,
            'group_size': self.group_size,
            'status': self.status,
            'ticket_amount': float(self.ticket_amount),
            'payment_status': self.payment_status
        }


class Trajectory:
    def __init__(self, trajectory_id: Optional[int] = None, tourist_id: str = '',
                 location_time: Optional[datetime] = None, latitude: float = 0.0,
                 longitude: float = 0.0, area_id: str = '', off_route: bool = False):
        self.trajectory_id = trajectory_id
        self.tourist_id = tourist_id
        self.location_time = location_time or datetime.now()
        self.latitude = latitude
        self.longitude = longitude
        self.area_id = area_id
        self.off_route = off_route

    def to_dict(self) -> Dict[str, Any]:
        return {
            'trajectory_id': self.trajectory_id,
            'tourist_id': self.tourist_id,
            'location_time': self.location_time.isoformat() if self.location_time else None,
            'latitude': float(self.latitude),
            'longitude': float(self.longitude),
            'area_id': self.area_id,
            'off_route': self.off_route
        }


class FlowControl:
    def __init__(self, area_id: str, area_name: str, daily_capacity: int,
                 current_visitors: int = 0, warning_threshold: float = 0.8,
                 status: str = 'normal'):
        self.area_id = area_id
        self.area_name = area_name
        self.daily_capacity = daily_capacity
        self.current_visitors = current_visitors
        self.warning_threshold = warning_threshold
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            'area_id': self.area_id,
            'area_name': self.area_name,
            'daily_capacity': self.daily_capacity,
            'current_visitors': self.current_visitors,
            'warning_threshold': float(self.warning_threshold),
            'status': self.status,
            'usage_percentage': round((self.current_visitors / self.daily_capacity) * 100, 2),
            'is_warning': self.current_visitors >= self.daily_capacity * self.warning_threshold
        }