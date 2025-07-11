# CRITICAL FIX: Group game answer handling

## Problem: Only first player's answer was accepted in group chat

## Root cause:
- game_state.awaiting_answer = False after first answer
- Blocked all subsequent answers from other participants

## Solution implemented:
1. Added current_question_answers tracking in GameState
2. New methods: add_user_answer, has_user_answered, should_wait_for_more_answers
3. Proper participant validation and duplicate answer prevention
4. Team mode: only captain answers, Individual mode: all participants answer
5. Enhanced timeout handling showing who answered/didn't answer

## Status: FIXED - All participants can now answer in group games

