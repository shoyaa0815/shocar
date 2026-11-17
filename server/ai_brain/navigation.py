import math

TURN_SECONDS = 0.2
YELLOW_HOLD_SECONDS = 3.0
DEFAULT_SPIN_SECONDS = 4.0


class Navigation:
    def __init__(self, spin_seconds=DEFAULT_SPIN_SECONDS):
        if not math.isfinite(spin_seconds) or not TURN_SECONDS <= spin_seconds <= 60:
            raise ValueError('AUTO_SPIN_SECONDS must be between 0.2 and 60 seconds')
        self.spin_seconds = spin_seconds
        self.reset()

    def reset(self):
        self.command = "stop"
        self.candidate = None
        self.count = 0
        self.sequence = None
        self.search_phase = None
        self.search_direction = None
        self.search_turns = 0
        self.spin_elapsed = 0.0
        self.turn_started = None
        self.turn_until = None
        self.stopped_at = None
        self.failure = None
        self.yellow_since = None
        self.yellow_last_frame = None

    @property
    def search_reason(self):
        if self.search_phase == 'turning':
            direction = 'ซ้าย' if self.search_direction == 'left' else 'ขวา'
            return f'กำลังหาทาง{direction} · หมุนสะสม {self.spin_elapsed:.1f}/{self.spin_seconds:g} วินาที'
        if self.search_phase == 'checking':
            return 'หยุดดูทาง · รอภาพหลังหยุดและยืนยันทางโล่ง 3 เฟรมใหม่'
        if self.search_phase == 'waiting':
            return 'หยุดก่อนหมุนหาทาง · รอภาพใหม่หลังหยุด'
        if self.search_phase == 'parked':
            return 'ครบเวลาหมุนหนึ่งรอบโดยประมาณ · หยุดรอทางโล่ง 3 เฟรมใหม่'
        return self.failure

    def acknowledge_stop(self, now):
        if self.search_phase in ('waiting', 'checking', 'parked') and self.stopped_at is None:
            self.stopped_at = now
            if self.turn_started is not None:
                self.spin_elapsed += max(0.0, now - self.turn_started)
                self.turn_started = None
            if self.spin_elapsed >= self.spin_seconds - 1e-9:
                self.search_phase = 'parked'

    def _search(self, sides, sequence, now, received_at):
        if self.search_phase == 'turning':
            if now < self.turn_until:
                self.sequence = sequence
                return self.command
            self.search_phase = 'checking'
            self.stopped_at = None
            self.candidate, self.count = None, 0
            self.sequence = sequence
            self.command = 'stop'
            return self.command
        if (self.stopped_at is None or received_at is None
                or not math.isfinite(received_at) or not self.stopped_at < received_at <= now
                or sequence <= self.sequence):
            return 'stop'
        self.sequence = sequence
        if sides.get('left') is False and sides.get('right') is False:
            self.count += 1
            if self.count >= 3:
                self.search_phase = None
                self.candidate = self.command = 'forward'
                return self.command
            return 'stop'
        self.count = 0
        if self.search_phase == 'parked':
            return 'stop'
        remaining = self.spin_seconds - self.spin_elapsed
        if remaining <= 1e-9:
            self.search_phase = 'parked'
            return 'stop'
        self.search_turns += 1
        self.search_phase = 'turning'
        self.turn_started = now
        self.turn_until = now + min(TURN_SECONDS, remaining)
        self.command = self.search_direction
        return self.command

    def decide(self, sides: dict, sequence: int, *, scores=None, now=None, received_at=None,
               fresh_seconds=3.0) -> str:
        if self.search_phase is not None:
            return self._search(sides, sequence, now, received_at)
        if self.sequence is not None and sequence <= self.sequence:
            return self.command
        left, right = sides.get('left'), sides.get('right')
        unknown = type(left) is not bool or type(right) is not bool
        blocked = left is True and right is True
        direction = None
        if unknown:
            self.sequence = sequence
            self.command, self.candidate, self.count = 'stop', None, 0
            if (left is None and right is None and now is not None
                    and received_at is not None and math.isfinite(received_at)
                    and 0 <= now - received_at < fresh_seconds):
                if (self.yellow_last_frame is None or received_at <= self.yellow_last_frame
                        or received_at - self.yellow_last_frame >= fresh_seconds):
                    self.yellow_since = now
                self.yellow_last_frame = received_at
                if now - self.yellow_since >= YELLOW_HOLD_SECONDS:
                    self.reset()
                    self.sequence = sequence
                    self.search_phase = 'waiting'
                    self.search_direction = 'right'
            else:
                self.yellow_since = self.yellow_last_frame = None
            return 'stop'
        self.yellow_since = self.yellow_last_frame = None
        if blocked and isinstance(scores, dict):
            values = [scores.get(side) for side in ('left', 'right')]
            if all(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1
                   for value in values):
                direction = 'left' if values[0] < values[1] else 'right'
        if direction is not None and now is not None:
            self.reset()
            self.sequence = sequence
            self.search_phase = 'waiting'
            self.search_direction = direction
            return 'stop'
        if type(left) is not bool or type(right) is not bool or (left and right):
            self.reset()
            self.sequence = sequence
            return "stop"
        self.sequence = sequence
        if left:
            desired = "right"
        elif right:
            desired = "left"
        else:
            desired = "forward"
        if desired != self.candidate:
            self.candidate, self.count = desired, 1
        else:
            self.count += 1
        if self.count >= 3:
            self.command = desired
        elif desired != self.command:
            self.command = "stop"
        return self.command
