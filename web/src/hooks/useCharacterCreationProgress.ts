// web/src/hooks/useCharacterCreationProgress.ts
import { useState, useCallback } from 'react';

interface CharacterCreationStep1 {
  name: string;
  campaign_id: number;
}

interface CharacterCreationStep2 {
  race: string;
  variant: string;
  custom_ability_choices?: {[key: string]: number};
}

interface CharacterCreationStep3 {
  class_name: string;
  subclass?: string;
}

interface AbilityScores {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

interface CharacterCreationStep4 {
  method: string;
  base_scores: AbilityScores;
  point_buy_remaining?: number;
  rolled_stats?: number[][];
}

interface CharacterCreationStep5 {
  background: string;
  skill_choices: string[];
  language_choices?: string[];
  tool_proficiencies?: string[];
}

interface CharacterCreationStep6 {
  feats: string[];
  additional_ability_increases?: {[key: string]: number};
  equipment_choices?: {[key: string]: string};
}

interface CharacterCreationProgress {
  step1?: CharacterCreationStep1;
  step2?: CharacterCreationStep2;
  step3?: CharacterCreationStep3;
  step4?: CharacterCreationStep4;
  step5?: CharacterCreationStep5;
  step6?: CharacterCreationStep6;
  current_step: number;
}

interface CharacterCreationSummary {
  current_step: number;
  completed_steps: number[];
  selections: {
    name?: string;
    campaign_id?: number;
    race?: any;
    class?: any;
    abilities?: any;
    background?: any;
    final?: any;
  };
  derived_stats?: any;
}

export const useCharacterCreationProgress = () => {
  const [progress, setProgress] = useState<CharacterCreationProgress>({
    current_step: 1
  });
  const [summary, setSummary] = useState<CharacterCreationSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateStep = useCallback((stepNumber: number, stepData: any) => {
    setProgress(prev => {
      const updated = {
        ...prev,
        [`step${stepNumber}`]: stepData,
        current_step: stepNumber
      };
      return updated;
    });
  }, []);

  const nextStep = useCallback(() => {
    setProgress(prev => ({
      ...prev,
      current_step: Math.min(prev.current_step + 1, 6)
    }));
  }, []);

  const previousStep = useCallback(() => {
    setProgress(prev => ({
      ...prev,
      current_step: Math.max(prev.current_step - 1, 1)
    }));
  }, []);

  const goToStep = useCallback((stepNumber: number) => {
    setProgress(prev => ({
      ...prev,
      current_step: Math.max(1, Math.min(stepNumber, 6))
    }));
  }, []);

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/character-creation/get-summary', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(progress),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const summaryData = await response.json();
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch summary');
      console.error('Error fetching character creation summary:', err);
    } finally {
      setLoading(false);
    }
  }, [progress]);

  const resetProgress = useCallback(() => {
    setProgress({ current_step: 1 });
    setSummary(null);
    setError(null);
  }, []);

  const getCompletedSteps = useCallback((): number[] => {
    const completed: number[] = [];
    if (progress.step1) completed.push(1);
    if (progress.step2) completed.push(2);
    if (progress.step3) completed.push(3);
    if (progress.step4) completed.push(4);
    if (progress.step5) completed.push(5);
    if (progress.step6) completed.push(6);
    return completed;
  }, [progress]);

  const isStepComplete = useCallback((stepNumber: number): boolean => {
    return getCompletedSteps().includes(stepNumber);
  }, [getCompletedSteps]);

  const canGoToStep = useCallback((stepNumber: number): boolean => {
    if (stepNumber === 1) return true;
    // Can go to a step if the previous step is completed
    return isStepComplete(stepNumber - 1);
  }, [isStepComplete]);

  const getStepData = useCallback((stepNumber: number) => {
    return progress[`step${stepNumber}` as keyof CharacterCreationProgress];
  }, [progress]);

  return {
    progress,
    summary,
    loading,
    error,
    currentStep: progress.current_step,
    completedSteps: getCompletedSteps(),
    updateStep,
    nextStep,
    previousStep,
    goToStep,
    fetchSummary,
    resetProgress,
    isStepComplete,
    canGoToStep,
    getStepData
  };
};