// web/src/components/EnhancedCharacterCreator.tsx
import React, { useEffect } from 'react';
import CharacterCreationSummary from './CharacterCreationSummary';
import { useCharacterCreationProgress } from '../hooks/useCharacterCreationProgress';
import '../styles/CharacterCreationSummary.css';
import '../styles/EnhancedCharacterCreator.css';

interface EnhancedCharacterCreatorProps {
  campaignId: number;
  onCharacterCreated?: (characterId: number) => void;
}

const EnhancedCharacterCreator: React.FC<EnhancedCharacterCreatorProps> = ({
  campaignId,
  onCharacterCreated
}) => {
  const {
    progress,
    summary,
    loading,
    error,
    currentStep,
    completedSteps,
    updateStep,
    nextStep,
    previousStep,
    fetchSummary,
    resetProgress,
    isStepComplete,
    canGoToStep
  } = useCharacterCreationProgress();

  // Fetch summary whenever progress changes
  useEffect(() => {
    fetchSummary();
  }, [progress, fetchSummary]);

  const handleStepUpdate = (stepNumber: number, stepData: any) => {
    updateStep(stepNumber, stepData);
  };

  const handleNext = () => {
    if (currentStep < 6) {
      nextStep();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      previousStep();
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <Step1BasicInfo
            campaignId={campaignId}
            initialData={progress.step1}
            onUpdate={(data) => handleStepUpdate(1, data)}
            onNext={handleNext}
          />
        );
      case 2:
        return (
          <Step2RaceSelection
            initialData={progress.step2}
            onUpdate={(data) => handleStepUpdate(2, data)}
            onNext={handleNext}
            onPrevious={handlePrevious}
          />
        );
      case 3:
        return (
          <Step3ClassSelection
            initialData={progress.step3}
            onUpdate={(data) => handleStepUpdate(3, data)}
            onNext={handleNext}
            onPrevious={handlePrevious}
          />
        );
      case 4:
        return (
          <Step4AbilityScores
            initialData={progress.step4}
            raceData={progress.step2}
            onUpdate={(data) => handleStepUpdate(4, data)}
            onNext={handleNext}
            onPrevious={handlePrevious}
          />
        );
      case 5:
        return (
          <Step5BackgroundSkills
            initialData={progress.step5}
            classData={progress.step3}
            onUpdate={(data) => handleStepUpdate(5, data)}
            onNext={handleNext}
            onPrevious={handlePrevious}
          />
        );
      case 6:
        return (
          <Step6FeatsAndFinal
            initialData={progress.step6}
            allProgressData={progress}
            onUpdate={(data) => handleStepUpdate(6, data)}
            onPrevious={handlePrevious}
            onFinish={onCharacterCreated}
          />
        );
      default:
        return <div>Invalid step</div>;
    }
  };

  return (
    <div className="enhanced-character-creator">
      <div className="creator-header">
        <h2>Create New Character</h2>
        <div className="step-navigation">
          {[1, 2, 3, 4, 5, 6].map(step => (
            <button
              key={step}
              className={`step-nav-button ${
                step === currentStep ? 'current' :
                isStepComplete(step) ? 'completed' :
                canGoToStep(step) ? 'available' : 'disabled'
              }`}
              onClick={() => canGoToStep(step) && updateStep(step, progress[`step${step}` as keyof typeof progress])}
              disabled={!canGoToStep(step)}
              title={getStepTitle(step)}
            >
              {step}
            </button>
          ))}
        </div>
      </div>

      <div className="creator-content">
        <div className="creator-main">
          {error && (
            <div className="error-message">
              Error: {error}
              <button onClick={fetchSummary} className="retry-button">
                Retry
              </button>
            </div>
          )}

          <div className="step-content">
            {renderStepContent()}
          </div>
        </div>

        <div className="creator-sidebar">
          {summary && (
            <CharacterCreationSummary
              summary={summary}
              currentStep={currentStep}
            />
          )}
          {loading && (
            <div className="loading-summary">
              <div className="spinner"></div>
              <p>Updating character preview...</p>
            </div>
          )}
        </div>
      </div>

      <div className="creator-footer">
        <div className="step-info">
          Step {currentStep} of 6: {getStepTitle(currentStep)}
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${(completedSteps.length / 6) * 100}%` }}
          ></div>
        </div>
      </div>
    </div>
  );
};

const getStepTitle = (step: number): string => {
  const titles = {
    1: "Basic Information",
    2: "Race & Variant",
    3: "Class Selection",
    4: "Ability Scores",
    5: "Background & Skills",
    6: "Feats & Finalization"
  };
  return titles[step as keyof typeof titles] || `Step ${step}`;
};

// Placeholder step components - these would be implemented separately
const Step1BasicInfo: React.FC<any> = ({ campaignId, initialData, onUpdate, onNext }) => (
  <div className="step-placeholder">
    <h3>Step 1: Basic Information</h3>
    <p>Character name and campaign selection</p>
    <p>Campaign ID: {campaignId}</p>
    {/* Implementation would go here */}
    <button onClick={onNext} className="next-button">Next</button>
  </div>
);

const Step2RaceSelection: React.FC<any> = ({ initialData, onUpdate, onNext, onPrevious }) => (
  <div className="step-placeholder">
    <h3>Step 2: Race & Variant Selection</h3>
    <p>Choose your character's race and variant</p>
    {/* Implementation would go here */}
    <div className="step-buttons">
      <button onClick={onPrevious} className="previous-button">Previous</button>
      <button onClick={onNext} className="next-button">Next</button>
    </div>
  </div>
);

const Step3ClassSelection: React.FC<any> = ({ initialData, onUpdate, onNext, onPrevious }) => (
  <div className="step-placeholder">
    <h3>Step 3: Class Selection</h3>
    <p>Choose your character's class (subclass selected later based on class)</p>
    {/* Implementation would go here */}
    <div className="step-buttons">
      <button onClick={onPrevious} className="previous-button">Previous</button>
      <button onClick={onNext} className="next-button">Next</button>
    </div>
  </div>
);

const Step4AbilityScores: React.FC<any> = ({ initialData, raceData, onUpdate, onNext, onPrevious }) => (
  <div className="step-placeholder">
    <h3>Step 4: Ability Scores</h3>
    <p>Set your character's ability scores</p>
    {raceData && (
      <div className="race-context">
        <strong>Selected Race:</strong> {raceData.variant} ({raceData.race})
      </div>
    )}
    {/* Implementation would go here */}
    <div className="step-buttons">
      <button onClick={onPrevious} className="previous-button">Previous</button>
      <button onClick={onNext} className="next-button">Next</button>
    </div>
  </div>
);

const Step5BackgroundSkills: React.FC<any> = ({ initialData, classData, onUpdate, onNext, onPrevious }) => (
  <div className="step-placeholder">
    <h3>Step 5: Background & Skills</h3>
    <p>Choose background and skill proficiencies</p>
    {classData && (
      <div className="class-context">
        <strong>Selected Class:</strong> {classData.class_name}
        {classData.subclass && ` (${classData.subclass})`}
      </div>
    )}
    {/* Implementation would go here */}
    <div className="step-buttons">
      <button onClick={onPrevious} className="previous-button">Previous</button>
      <button onClick={onNext} className="next-button">Next</button>
    </div>
  </div>
);

const Step6FeatsAndFinal: React.FC<any> = ({ initialData, allProgressData, onUpdate, onPrevious, onFinish }) => (
  <div className="step-placeholder">
    <h3>Step 6: Feats & Finalization</h3>
    <p>Choose feats and finalize your character</p>
    {/* Implementation would go here */}
    <div className="step-buttons">
      <button onClick={onPrevious} className="previous-button">Previous</button>
      <button onClick={() => onFinish && onFinish(1)} className="finish-button">Create Character</button>
    </div>
  </div>
);

export default EnhancedCharacterCreator;