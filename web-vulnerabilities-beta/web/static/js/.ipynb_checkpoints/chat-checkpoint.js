const chatBox = document.getElementById('chat-box');
const input = document.getElementById('question');
const button = document.getElementById('send-btn');

button.addEventListener('click', async () => {
    const question = input.value;
    if (!question) return;

    chatBox.innerHTML += `<div class="user-msg">You: ${question}</div>`;
    input.value = '';

    const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
    });

    const data = await res.json();
    chatBox.innerHTML += `<div class="tutor-msg">Tutor: ${data.answer}</div>`;
    chatBox.scrollTop = chatBox.scrollHeight;
});