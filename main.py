import pygame
import numpy as np
import math
import random

# 설정
WIDTH, HEIGHT = 800, 600
FPS = 60

# 색상
SKY_COLOR = (100, 150, 255)
GRASS_COLOR = (34, 139, 34)

class GameObject:
    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type # 'tree', 'box', 'ai'
        self.active = True
        self.radius = 25
        
        # AI 전용 변수
        if type == 'ai':
            self.angle = 0
            self.speed = random.uniform(5, 7)
            self.color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
            self.target_radius = 800 + random.uniform(-40, 40) # 트랙 위 무작위 라인

class KartGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("KartPy 2.5D - AI Competitors")
        self.clock = pygame.time.Clock()
        
        # 1. 트랙 설정
        self.track_size = 2048
        self.track_center = (self.track_size // 2, self.track_size // 2)
        self.track_surface = pygame.Surface((self.track_size, self.track_size))
        self.create_test_track()
        self.track_pixels = pygame.surfarray.array3d(self.track_surface)
        
        # 2. 오브젝트 생성 (나무, 아이템 박스, AI)
        self.objects = []
        for _ in range(40):
            self.objects.append(GameObject(random.randint(0, self.track_size), random.randint(0, self.track_size), 'tree'))
        for _ in range(12):
            self.objects.append(GameObject(random.randint(0, self.track_size), random.randint(0, self.track_size), 'box'))
        
        # AI 경쟁자 5명 추가
        for i in range(5):
            # 트랙 위의 시작 지점 계산
            start_angle = (i * math.pi * 2 / 5)
            ax = self.track_center[0] + math.cos(start_angle) * 800
            ay = self.track_center[1] + math.sin(start_angle) * 800
            ai = GameObject(ax, ay, 'ai')
            ai.angle = start_angle + math.pi/2 # 주행 방향
            self.objects.append(ai)
            
        # 3. 플레이어 상태
        self.pos_x, self.pos_y = self.track_center[0] + 800, self.track_center[1]
        self.angle = math.pi / 2
        self.move_angle = math.pi / 2
        self.speed = 0
        self.max_speed = 8.0
        self.turn_speed = 0.04
        
        self.is_drifting, self.drift_gauge, self.drift_direction = False, 0, 0
        self.boost_timer = 0
        
        # 렌더링 설정
        self.horizon, self.scaling = HEIGHT // 2, 180

    def create_test_track(self):
        self.track_surface.fill(GRASS_COLOR)
        tile_size = 128
        for y in range(0, self.track_size, tile_size):
            for x in range(0, self.track_size, tile_size):
                if (x // tile_size + y // tile_size) % 2 == 0:
                    pygame.draw.rect(self.track_surface, (50, 150, 50), (x, y, tile_size, tile_size))
        pygame.draw.circle(self.track_surface, (80, 80, 80), self.track_center, 800, 150) # 아스팔트
        pygame.draw.circle(self.track_surface, (255, 255, 255), self.track_center, 800, 5) # 중앙선

    def update_ai(self):
        for obj in self.objects:
            if obj.type == 'ai':
                # 트랙 중심으로부터의 각도와 거리 계산
                dx, dy = obj.x - self.track_center[0], obj.y - self.track_center[1]
                current_dist = math.sqrt(dx**2 + dy**2)
                current_angle = math.atan2(dy, dx)
                
                # 다음 목표 각도 (원형 주행)
                next_angle = current_angle + (obj.speed / obj.target_radius)
                
                # 새로운 위치 계산 (약간의 조향 보정 포함)
                obj.x = self.track_center[0] + math.cos(next_angle) * obj.target_radius
                obj.y = self.track_center[1] + math.sin(next_angle) * obj.target_radius
                obj.angle = next_angle + math.pi/2 # 진행 방향 업데이트

    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        # AI 업데이트
        self.update_ai()
        
        # [플레이어 조작 및 물리]
        current_turn_speed = self.turn_speed * 1.6 if self.is_drifting else self.turn_speed
        if self.is_drifting: self.drift_gauge = min(self.drift_gauge + 1.5, 100)
            
        if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and abs(self.speed) > 2 and not self.is_drifting:
            if keys[pygame.K_LEFT]: self.is_drifting, self.drift_direction = True, -1
            elif keys[pygame.K_RIGHT]: self.is_drifting, self.drift_direction = True, 1
        
        if self.is_drifting and not (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]):
            if self.drift_gauge > 40: self.boost_timer, self.speed = int(self.drift_gauge), self.speed + 3.0
            self.is_drifting, self.drift_gauge, self.drift_direction = False, 0, 0

        if keys[pygame.K_LEFT]: self.angle -= current_turn_speed
        if keys[pygame.K_RIGHT]: self.angle += current_turn_speed
            
        lerp_f = 0.04 if self.is_drifting else 0.15
        diff = (self.angle - self.move_angle + math.pi) % (2*math.pi) - math.pi
        self.move_angle += diff * lerp_f
            
        if self.boost_timer > 0: self.speed, self.boost_timer = self.max_speed + 4.0, self.boost_timer - 1
        else:
            if keys[pygame.K_UP]: self.speed = min(self.speed + 0.15, self.max_speed)
            elif keys[pygame.K_DOWN]: self.speed = max(self.speed - 0.2, -self.max_speed/2)
            else: self.speed = max(0, self.speed - 0.06) if self.speed > 0 else min(0, self.speed + 0.06)
            
        # 충돌 및 위치 업데이트
        new_x, new_y = (self.pos_x + math.cos(self.move_angle) * self.speed) % self.track_size, (self.pos_y + math.sin(self.move_angle) * self.speed) % self.track_size
        for obj in self.objects:
            if not obj.active: continue
            d = math.sqrt((new_x - obj.x)**2 + (new_y - obj.y)**2)
            if d < obj.radius:
                if obj.type == 'tree': self.speed *= 0.3
                elif obj.type == 'box': obj.active, self.boost_timer = False, 50
                elif obj.type == 'ai': self.speed *= 0.5 # AI와 부딪히면 감속
        self.pos_x, self.pos_y = new_x, new_y

    def draw(self):
        # 1. 바닥 렌더링
        self.screen.fill(SKY_COLOR, (0, 0, WIDTH, self.horizon))
        y_indices = np.arange(self.horizon + 1, HEIGHT)
        distances = (self.scaling * 100) / (y_indices - self.horizon)
        sin_a, cos_a = math.sin(self.angle), math.cos(self.angle)
        x_indices = np.arange(WIDTH)
        screen_array = pygame.surfarray.array3d(self.screen)
        
        for i, screen_y in enumerate(y_indices):
            dist = distances[i]
            h_scale = dist / self.scaling
            dx, dy = -sin_a * h_scale, cos_a * h_scale
            sx, sy = self.pos_x + (cos_a * dist) - (dx * WIDTH/2), self.pos_y + (sin_a * dist) - (dy * WIDTH/2)
            sxs, sys = (sx + x_indices * dx).astype(int) % self.track_size, (sy + x_indices * dy).astype(int) % self.track_size
            screen_array[:, screen_y] = self.track_pixels[sxs, sys]
        pygame.surfarray.blit_array(self.screen, screen_array)

        # 2. 모든 오브젝트(AI 포함) 빌보드 렌더링
        render_objs = []
        for obj in self.objects:
            if not obj.active: continue
            dx, dy = obj.x - self.pos_x, obj.y - self.pos_y
            # 맵 래핑 보정
            if dx > self.track_size/2: dx -= self.track_size
            elif dx < -self.track_size/2: dx += self.track_size
            if dy > self.track_size/2: dy -= self.track_size
            elif dy < -self.track_size/2: dy += self.track_size
            
            depth = dx * cos_a + dy * sin_a
            side = dx * -sin_a + dy * cos_a
            if depth > 5: render_objs.append((depth, side, obj))
        
        render_objs.sort(key=lambda x: x[0], reverse=True)
        
        for depth, side, obj in render_objs:
            sy = self.horizon + (self.scaling * 100) / depth
            if sy < self.horizon or sy > HEIGHT + 200: continue
            sx = WIDTH//2 + (side * (self.scaling * 100) / depth)
            scale = (self.scaling * 2) / depth
            
            if 0 < sx < WIDTH:
                w, h = 40 * scale, 60 * scale
                if obj.type == 'tree':
                    pygame.draw.rect(self.screen, (100, 50, 0), (sx - w/4, sy - h, w/2, h))
                    pygame.draw.circle(self.screen, (0, 100, 0), (int(sx), int(sy - h)), int(w/2))
                elif obj.type == 'box':
                    pygame.draw.rect(self.screen, (0, 100, 255), (sx - w/2, sy - h, w, h))
                    pygame.draw.rect(self.screen, (255, 255, 255), (sx - w/2, sy - h, w, h), 2)
                elif obj.type == 'ai':
                    # AI 카트 그리기 (플레이어 시점에 따른 회전 각도 보정)
                    pygame.draw.rect(self.screen, obj.color, (sx - w/2, sy - h, w, h))
                    pygame.draw.rect(self.screen, (0, 0, 0), (sx - w/2, sy - h, w, h), 2)

        # 3. 플레이어 카트 및 UI
        color = (220, 20, 60) if self.boost_timer == 0 else (255, 255, 0)
        car_surf = pygame.Surface((44, 64), pygame.SRCALPHA)
        pygame.draw.rect(car_surf, color, (2, 2, 40, 60)); pygame.draw.rect(car_surf, (0, 0, 0), (2, 2, 40, 60), 2)
        v_angle = -25 if self.drift_direction == 1 else (25 if self.drift_direction == -1 else 0)
        rot_car = pygame.transform.rotate(car_surf, v_angle)
        self.screen.blit(rot_car, rot_car.get_rect(center=(WIDTH//2, HEIGHT - 90)))
        
        if self.is_drifting:
            pygame.draw.rect(self.screen, (255, 200, 0), (WIDTH//2-50, HEIGHT-150, self.drift_gauge, 10))
        
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
            self.handle_input(); self.draw()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    game = KartGame()
    game.run()
