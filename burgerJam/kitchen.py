"""Pixel-art kitchen and flour-sack dummy, drawn in the game's existing palette."""

import pygame

from .combat import FLOOR, HEIGHT, WIDTH


def make_kitchen():
    # Draw at half resolution and scale without smoothing to match the jam sprites.
    scene = pygame.Surface((WIDTH // 2, HEIGHT // 2))
    ink, cream = (22, 27, 34), (255, 242, 212)
    steel, shadow, light = (106, 117, 119), (48, 57, 62), (167, 177, 174)
    scene.fill((66, 65, 60))
    pygame.draw.rect(scene, (43, 46, 47), (0, 0, 600, 75))
    pygame.draw.rect(scene, (108, 70, 48), (0, 69, 600, 9))
    pygame.draw.rect(scene, (207, 149, 80), (0, 77, 600, 3))
    # Warm subway tiles, with a few worn corners instead of smooth gradients.
    for row, y in enumerate(range(82, 237, 24)):
        for x in range(-30 if row % 2 else 0, 600, 48):
            color = (133, 130, 111) if (row + x // 48) % 4 else (145, 140, 120)
            pygame.draw.rect(scene, color, (x + 1, y + 1, 46, 22))
            pygame.draw.line(scene, (168, 161, 137), (x + 2, y + 2), (x + 45, y + 2))
    # Copper extractor hood and dark vent slots above the grill.
    pygame.draw.rect(scene, shadow, (266, 77, 69, 37))
    pygame.draw.rect(scene, (132, 88, 58), (272, 80, 57, 36))
    pygame.draw.polygon(scene, (155, 101, 62), [(217, 111), (383, 111), (406, 153), (194, 153)])
    pygame.draw.line(scene, (219, 163, 99), (217, 112), (383, 112), 3)
    pygame.draw.rect(scene, (67, 60, 53), (192, 152, 216, 13))
    for x in range(203, 402, 12):
        pygame.draw.line(scene, (36, 38, 38), (x, 154), (x - 3, 163), 4)
    pygame.draw.rect(scene, (247, 202, 119), (213, 165, 175, 3))
    # The flat-top grill: hot orange gaps, black grate and a couple of patties.
    pygame.draw.rect(scene, shadow, (198, 205, 204, 37))
    pygame.draw.rect(scene, (215, 106, 49), (208, 202, 184, 10))
    for x in range(208, 394, 8):
        pygame.draw.line(scene, (29, 32, 34), (x, 201), (x - 4, 213), 3)
    pygame.draw.ellipse(scene, (103, 59, 41), (238, 200, 30, 9))
    pygame.draw.ellipse(scene, (119, 68, 44), (327, 202, 28, 8))
    pygame.draw.rect(scene, steel, (199, 213, 202, 27))
    pygame.draw.line(scene, light, (200, 213), (400, 213), 2)
    for x in (224, 260, 336, 372):
        pygame.draw.circle(scene, ink, (x, 226), 5)
        pygame.draw.line(scene, (241, 164, 82), (x, 222), (x, 226), 2)
    for x, y in ((250, 189), (258, 180), (343, 191), (335, 181)):
        pygame.draw.lines(scene, (177, 166, 141), False, [(x, y), (x - 3, y - 6), (x + 1, y - 12)], 2)
    # Refrigerator and a tiny chalk menu at the left.
    pygame.draw.rect(scene, shadow, (16, 98, 92, 143))
    pygame.draw.rect(scene, steel, (20, 101, 83, 137))
    pygame.draw.line(scene, light, (22, 103), (22, 235), 2)
    pygame.draw.line(scene, shadow, (22, 151), (101, 151), 3)
    for y in (121, 172):
        pygame.draw.rect(scene, ink, (91, y, 4, 17))
    pygame.draw.rect(scene, (119, 80, 49), (123, 97, 61, 67))
    pygame.draw.rect(scene, (35, 53, 48), (127, 101, 53, 59))
    font = pygame.font.Font(None, 14)
    for y, text in ((108, "THE GRILL"), (125, "FRESH HITS"), (139, "ALL DAY")):
        label = font.render(text, False, cream)
        scene.blit(label, label.get_rect(center=(154, y)))
    # Hanging kitchen tools and a side shelf with ketchup and mustard.
    pygame.draw.line(scene, shadow, (423, 111), (579, 111), 3)
    for x in (437, 465, 493):
        pygame.draw.line(scene, ink, (x, 113), (x, 139), 3)
    pygame.draw.ellipse(scene, shadow, (425, 136, 24, 25))
    pygame.draw.ellipse(scene, steel, (428, 139, 18, 19))
    pygame.draw.rect(scene, light, (458, 137, 15, 21))
    for x in (461, 466, 471):
        pygame.draw.line(scene, shadow, (x, 140), (x, 153))
    pygame.draw.ellipse(scene, steel, (486, 137, 14, 25))
    pygame.draw.rect(scene, (87, 63, 47), (421, 197, 162, 8))
    for x, color in ((448, (211, 64, 44)), (471, (233, 182, 44))):
        pygame.draw.rect(scene, color, (x, 167, 15, 30), border_radius=3)
        pygame.draw.rect(scene, color, (x + 5, 161, 5, 9))
        pygame.draw.rect(scene, cream, (x + 3, 180, 9, 8))
    pygame.draw.rect(scene, (167, 126, 76), (506, 187, 54, 10), border_radius=2)
    pygame.draw.rect(scene, (190, 154, 100), (511, 183, 44, 4))
    # Prep counter, drawers, and an open, darker practice area in front.
    pygame.draw.rect(scene, shadow, (0, 239, 600, 9))
    pygame.draw.rect(scene, light, (0, 237, 600, 3))
    pygame.draw.rect(scene, (57, 63, 63), (0, 248, 600, FLOOR // 2 - 248))
    for x in range(0, 600, 75):
        pygame.draw.rect(scene, (72, 79, 78), (x + 2, 249, 70, 40))
        pygame.draw.rect(scene, (25, 30, 32), (x + 25, 256, 24, 3))
    pygame.draw.line(scene, ink, (0, 291), (600, 291), 5)
    for y in range(FLOOR // 2, HEIGHT // 2, 24):
        for x in range(0, WIDTH // 2, 40):
            color = (44, 50, 51) if (x // 40 + y // 24) % 2 else (64, 69, 65)
            pygame.draw.rect(scene, color, (x + 1, y + 1, 38, 22))
    return pygame.transform.scale(scene, (WIDTH, HEIGHT))


def make_dummy():
    dummy = pygame.Surface((100, 100), pygame.SRCALPHA)
    # A flour sack on a spring stand, with stitched eyes and a painted target.
    pygame.draw.rect(dummy, (105, 76, 49), (19, 9, 64, 76), border_radius=19)
    pygame.draw.rect(dummy, (207, 172, 114), (20, 9, 55, 73), border_radius=18)
    pygame.draw.rect(dummy, (231, 202, 145), (27, 14, 14, 58), border_radius=7)
    for x in (24, 75):
        for y in range(27, 71, 10):
            pygame.draw.line(dummy, (116, 83, 50), (x - 2, y), (x + 2, y + 3), 2)
    for x in (37, 62):
        pygame.draw.line(dummy, (53, 49, 44), (x - 4, 25), (x + 4, 33), 2)
        pygame.draw.line(dummy, (53, 49, 44), (x + 4, 25), (x - 4, 33), 2)
    pygame.draw.circle(dummy, (179, 64, 45), (50, 59), 20, 4)
    pygame.draw.circle(dummy, (179, 64, 45), (50, 59), 9, 3)
    pygame.draw.circle(dummy, (244, 204, 122), (50, 59), 3)
    pygame.draw.line(dummy, (102, 114, 117), (45, 83), (55, 89), 3)
    pygame.draw.line(dummy, (157, 167, 165), (55, 83), (45, 90), 3)
    pygame.draw.rect(dummy, (68, 77, 81), (27, 91, 47, 7), border_radius=2)
    pygame.draw.line(dummy, (155, 163, 158), (30, 92), (70, 92), 2)
    return dummy
