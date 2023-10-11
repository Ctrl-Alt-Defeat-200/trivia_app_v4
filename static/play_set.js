// play_set.js

const questionContainer = document.getElementById('question-container');
const questionText = document.getElementById('question-text');
const optionsContainer = document.getElementById('options-container');
const answerForm = document.getElementById('answer-form');
const submitButton = document.getElementById('submit-answer');
const scoreContainer = document.getElementById('score-container');
const scoreText = document.getElementById('score');

let currentQuestionIndex = 0;
let score = 0;

// Define your questions and answers here based on Flask data
const questions = "{{ questions }}";
const questionAnswerDict = '{{ question_answer_dict }}';

// Timer variables
let timerInterval;
const timerElement = document.getElementById('timer');


// Function to load and display the current question
function loadCurrentQuestion() {
    const currentQuestion = questions[currentQuestionIndex];
    questionText.textContent = currentQuestion.question_text;

    // Clear previous options
    optionsContainer.innerHTML = '';

    // Create radio buttons for options
    currentQuestion.options.forEach((option, index) => {
        const optionRadio = document.createElement('input');
        optionRadio.type = 'radio';
        optionRadio.name = 'selected_option';
        optionRadio.value = option;
        optionRadio.id = `option${index + 1}`;

        const optionLabel = document.createElement('label');
        optionLabel.textContent = option;
        optionLabel.htmlFor = `option${index + 1}`;

        optionsContainer.appendChild(optionRadio);
        optionsContainer.appendChild(optionLabel);
        optionsContainer.appendChild(document.createElement('br'));
    });

    startTimer();
}

// Function to start the timer for a question
function startTimer() {
    let timeLeft = 10; // 10 seconds
    timerElement.textContent = timeLeft;

    timerInterval = setInterval(function () {
        timeLeft--;
        timerElement.textContent = timeLeft;

        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            checkAnswer(); // Automatically check answer when the timer runs out
        }
    }, 1000);
}


// Function to check the user's answer
function checkAnswer() {
    const selectedOption = document.querySelector('input[name="selected_option"]:checked');
    if (selectedOption) {
        const userAnswerValue = selectedOption.value;
        const currentQuestion = questions[currentQuestionIndex];
        const correctAnswers = questionAnswerDict[currentQuestion.id];

        if (correctAnswers.includes(userAnswerValue)) {
            score++;
            scoreText.textContent = score;
        }
        currentQuestionIndex++;
        if (currentQuestionIndex < questions.length) {
            loadCurrentQuestion();
        } else {
            questionContainer.innerHTML = '<h2>Game Over</h2>';
        }
    }
}

// Initial load
loadCurrentQuestion();

// Event listener for submit button
submitButton.addEventListener('click', checkAnswer);
