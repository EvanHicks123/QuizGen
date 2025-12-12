import os
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import requests
import json
import base64
import uvicorn
import random
import re
from io import BytesIO
from PyPDF2 import PdfReader
from zipfile import ZipFile
from lxml import etree

# --- ENV VAR CHECK ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not set. Please define it as an environment variable."
    )

app = FastAPI()

# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FRONTEND (React Single File) ---
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuizGen</title>
    
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg width='64' height='64' viewBox='0 0 64 64' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='8' y='8' width='48' height='48' rx='12' ry='12' fill='%23111827'/%3E%3Cpath d='M34 14L22 32h8l-2 18 12-18h-8z' fill='%23ffffff'/%3E%3C/svg%3E">

    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

        body {
            margin: 0;
            font-family: 'Inter', sans-serif;
            background: radial-gradient(circle at 50% -20%, #f3f4f6, #e5e7eb);
            height: 100vh;
            overflow: hidden;
            color: #1f2937;
        }

        .glass-panel {
            background: rgba(255, 255, 255, 0.65);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.8);
            box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.05);
        }

        .smooth-input {
            transition: all 0.3s ease;
            border: 1px solid transparent;
            background: rgba(255, 255, 255, 0.6);
        }
        .smooth-input:focus {
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
            outline: none;
        }

        /* --- MAXUIUX SLIDER CSS --- */
        .slider-container {
            position: relative;
            width: 100%;
            height: 10px;
            background: #D6D6DA;
            border-radius: 999px;
            cursor: pointer;
            margin: 15px 0;
        }

        .slider-progress {
            position: absolute;
            height: 100%;
            background: linear-gradient(117deg, #1f2937 0%, #4b5563 100%);
            border-radius: 999px;
            width: 0%;
            z-index: 1;
            pointer-events: none;
        }

        .slider-thumb-glass {
            position: absolute;
            top: 50%;
            transform: translate(-50%, -50%);
            width: 30px;
            height: 20px;
            border-radius: 999px;
            cursor: grab;
            z-index: 2;
            background-color: #fff;
            box-shadow: 0 1px 8px 0 rgba(0, 30, 63, 0.1), 0 0 2px 0 rgba(0, 9, 20, 0.1);
            overflow: hidden;
            transition: transform 0.15s ease, height 0.15s ease;
        }

        .slider-thumb-glass-filter {
            position: absolute;
            inset: 0;
            z-index: 0;
            backdrop-filter: blur(0.6px);
            -webkit-backdrop-filter: blur(0.6px);
            filter: url(#mini-liquid-lens);
        }

        .slider-thumb-glass-overlay {
            position: absolute;
            inset: 0;
            z-index: 1;
            background-color: rgba(255, 255, 255, 0.1);
        }

        .slider-thumb-glass-specular {
            position: absolute;
            inset: 0;
            z-index: 2;
            border-radius: inherit;
            box-shadow:
                inset 1px 1px 0 rgba(69, 168, 243, 0.2),
                inset 1px 3px 0 rgba(28, 63, 90, 0.05),
                inset 0 0 22px rgb(255 255 255 / 60%),
                inset -1px -1px 0 rgba(69, 168, 243, 0.12);
        }

        .slider-thumb-glass-filter,
        .slider-thumb-glass-overlay,
        .slider-thumb-glass-specular {
            opacity: 0;
            transition: opacity 0.2s ease;
        }

        /* Active State (Dragging) */
        .slider-thumb-glass.active {
            background-color: transparent;
            box-shadow: none;
            cursor: grabbing;
        }

        .slider-thumb-glass.active .slider-thumb-glass-filter,
        .slider-thumb-glass.active .slider-thumb-glass-overlay,
        .slider-thumb-glass.active .slider-thumb-glass-specular {
            opacity: 1;
        }

        .slider-thumb-glass:active {
            transform: translate(-50%, -50%) scaleY(0.98) scaleX(1.1);
        }

        /* Hover State */
        .slider-container:hover .slider-thumb-glass-filter,
        .slider-container:hover .slider-thumb-glass-overlay,
        .slider-container:hover .slider-thumb-glass-specular {
            opacity: 0.5;
        }

        /* --- BUTTONS --- */
        .smooth-btn {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .smooth-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        }
        .smooth-btn:active {
            transform: translateY(0px);
        }

        .animate-fade-in {
            animation: fadeIn 0.5s ease-out forwards;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <svg width="0" height="0" style="position: absolute; z-index: -1;">
        <filter id="mini-liquid-lens" x="-50%" y="-50%" width="200%" height="200%">
            <feImage x="0" y="0" result="normalMap" xlink:href="data:image/svg+xml;utf8,
            <svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'>
                <radialGradient id='invmap' cx='50%' cy='50%' r='75%'>
                <stop offset='0%' stop-color='rgb(128,128,255)'/>
                <stop offset='90%' stop-color='rgb(255,255,255)'/>
                </radialGradient>
                <rect width='100%' height='100%' fill='url(#invmap)'/>
            </svg>" />
            <feDisplacementMap in="SourceGraphic" in2="normalMap" scale="-252" xChannelSelector="R" yChannelSelector="G" result="displaced" />
            <feMerge>
                <feMergeNode in="displaced" />
            </feMerge>
        </filter>
    </svg>

    <div id="root"></div>

    <script type="text/babel">
        const { useState, useEffect, useRef } = React;

        // --- CUSTOM REACT SLIDER COMPONENT ---
        const GlassSlider = ({ min, max, value, onChange }) => {
            const sliderRef = useRef(null);
            const [isDragging, setIsDragging] = useState(false);

            const calculateValue = (clientX) => {
                if (!sliderRef.current) return;
                const rect = sliderRef.current.getBoundingClientRect();
                const offsetX = clientX - rect.left;
                let percent = offsetX / rect.width;
                percent = Math.max(0, Math.min(1, percent)); 
                const newValue = min + percent * (max - min);
                onChange(newValue);
            };

            const handleMouseDown = (e) => {
                setIsDragging(true);
                calculateValue(e.clientX);
                document.addEventListener('mousemove', handleMouseMove);
                document.addEventListener('mouseup', handleMouseUp);
            };

            const handleMouseMove = (e) => {
                calculateValue(e.clientX);
            };

            const handleMouseUp = () => {
                setIsDragging(false);
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
            };

            const handleTouchStart = (e) => {
                setIsDragging(true);
                calculateValue(e.touches[0].clientX);
                document.addEventListener('touchmove', handleTouchMove, { passive: false });
                document.addEventListener('touchend', handleTouchEnd);
            };

            const handleTouchMove = (e) => {
                calculateValue(e.touches[0].clientX);
            };

            const handleTouchEnd = () => {
                setIsDragging(false);
                document.removeEventListener('touchmove', handleTouchMove);
                document.removeEventListener('touchend', handleTouchEnd);
            };

            const percent = ((value - min) / (max - min)) * 100;

            return (
                <div 
                    className="slider-container" 
                    ref={sliderRef}
                    onMouseDown={handleMouseDown}
                    onTouchStart={handleTouchStart}
                >
                    <div className="slider-progress" style={{ width: `${percent}%` }}></div>
                    <div 
                        className={`slider-thumb-glass ${isDragging ? 'active' : ''}`} 
                        id="thumb"
                        style={{ left: `${percent}%` }}
                    >
                        <div className="slider-thumb-glass-filter"></div>
                        <div className="slider-thumb-glass-overlay"></div>
                        <div className="slider-thumb-glass-specular"></div>
                    </div>
                </div>
            );
        };

        function App() {
            const [view, setView] = useState('setup'); 
            const [topic, setTopic] = useState('');
            
            // Slider Value 
            const [numQuestions, setNumQuestions] = useState(10);
            
            const [file, setFile] = useState(null);
            const [loading, setLoading] = useState(false);
            
            const [questions, setQuestions] = useState([]);
            const [currentIdx, setCurrentIdx] = useState(0);
            const [score, setScore] = useState(0);
            const [userAnswers, setUserAnswers] = useState({});
            const [showFeedback, setShowFeedback] = useState(false);

            // Add More Logic
            const [moreQuestions, setMoreQuestions] = useState(10);
            const [addingMore, setAddingMore] = useState(false);

            const handleGenerate = async () => {
                if (!topic && !file) return alert("Please enter a topic or upload a file."); 
                
                setLoading(true);

                const formData = new FormData();
                formData.append('topic', topic || ""); 
                formData.append('num_questions', Math.round(numQuestions)); 
                if (file) formData.append('file', file);

                try {
                    const res = await fetch('/generate-quiz', { method: 'POST', body: formData });
                    if (!res.ok) {
                        const errText = await res.text();
                        try {
                            const errJson = JSON.parse(errText);
                            if (errJson.detail) {
                                if (Array.isArray(errJson.detail)) {
                                    throw new Error(errJson.detail.map(e => e.msg).join(", "));
                                }
                                throw new Error(errJson.detail);
                            }
                        } catch (e) {
                            throw new Error(errText);
                        }
                    }
                    const data = await res.json();
                    
                    setQuestions(data);
                    setScore(0);
                    setCurrentIdx(0);
                    setUserAnswers({});
                    setShowFeedback(false);
                    setView('quiz');
                } catch (err) {
                    alert("Error: " + err.message);
                } finally {
                    setLoading(false);
                }
            };

            const handleAddMoreQuestions = async () => {
                setAddingMore(true);

                const formData = new FormData();
                formData.append('topic', topic || "");
                formData.append('num_questions', Math.round(moreQuestions));
                if (file) formData.append('file', file);

                try {
                    const res = await fetch('/generate-quiz', { method: 'POST', body: formData });
                    if (!res.ok) {
                        const errText = await res.text();
                        throw new Error(errText);
                    }
                    const data = await res.json();
                    const startIndex = questions.length;
                    setQuestions(prev => [...prev, ...data]);
                    setShowFeedback(false);
                    setCurrentIdx(startIndex);
                    setView('quiz');
                } catch (err) {
                    alert("Error: " + err.message);
                } finally {
                    setAddingMore(false);
                }
            };

            const handleAnswer = (index) => {
                if (showFeedback) return;
                setUserAnswers(prev => ({...prev, [currentIdx]: index}));
                setShowFeedback(true);
                if (index === questions[currentIdx].correct) setScore(s => s + 1);
            };

            const handleSkip = () => {
                if (showFeedback) return;
                setUserAnswers(prev => ({...prev, [currentIdx]: 'skipped'}));
                moveToNext();
            };

            const moveToNext = () => {
                if (currentIdx < questions.length - 1) {
                    setCurrentIdx(c => c + 1);
                    setShowFeedback(false);
                } else {
                    setView('results');
                }
            };

            const startRetry = () => {
                const questionsToRetry = questions.filter((q, i) => {
                    const ans = userAnswers[i];
                    return ans === 'skipped' || ans !== q.correct;
                });
                if (questionsToRetry.length === 0) return;
                setQuestions(questionsToRetry);
                setScore(0);
                setCurrentIdx(0);
                setUserAnswers({});
                setShowFeedback(false);
                setView('quiz');
            };

            if (view === 'setup') return (
                <div className="h-screen w-full relative">
                    <div className="absolute top-8 left-10 z-10">
                        <div className="flex items-center gap-3">
                            <div className="bg-gray-900 text-white w-8 h-8 flex items-center justify-center rounded-lg shadow-lg">
                                <i className="fas fa-bolt text-sm"></i>
                            </div>
                            <h1 className="text-xl font-bold tracking-tight text-gray-800">QuizGen</h1>
                        </div>
                    </div>

                    <div className="flex items-center justify-center h-full p-4">
                        <div className="glass-panel w-full max-w-xl p-10 rounded-3xl animate-fade-in relative">
                            
                            <div className="mt-6 space-y-8">
                                <div className="text-center">
                                    <h2 className="text-2xl font-semibold text-gray-800">What are we learning?</h2>
                                </div>

                                <div className="relative">
                                    <textarea 
                                        className="smooth-input w-full rounded-2xl p-5 text-lg h-40 resize-none text-gray-800 placeholder-gray-400"
                                        placeholder="Type a topic, subject, or paste notes..."
                                        value={topic}
                                        onChange={e => setTopic(e.target.value)}
                                    ></textarea>
                                    
                                    <div className="absolute bottom-3 right-3">
                                        <label className="cursor-pointer group flex items-center gap-2">
                                            <input type="file" className="hidden" onChange={e => setFile(e.target.files[0])} />
                                            <span className={`text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-300 ${file ? 'bg-green-100 text-green-700' : 'bg-white shadow-sm text-gray-400 hover:text-gray-700 hover:shadow-md'}`}>
                                                {file ? file.name : <span><i className="fas fa-plus mr-1"></i> Context</span>}
                                            </span>
                                        </label>
                                    </div>
                                </div>

                                <div className="px-2">
                                    <div className="flex justify-between text-xs font-medium text-gray-400 mb-2 uppercase tracking-wide">
                                        <span>Length</span>
                                        <span>{Math.round(numQuestions)} Questions</span>
                                    </div>
                                    
                                    {/* --- CUSTOM GLASS SLIDER --- */}
                                    <GlassSlider 
                                        min={5} 
                                        max={50} 
                                        value={numQuestions} 
                                        onChange={setNumQuestions} 
                                    />
                                </div>

                                <button 
                                    onClick={handleGenerate}
                                    disabled={loading}
                                    className="smooth-btn w-full bg-gray-900 text-white h-14 rounded-2xl font-medium text-lg disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {loading ? <i className="fas fa-circle-notch fa-spin"></i> : "Generate Quiz"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            );

            if (view === 'quiz') {
                const q = questions[currentIdx];
                const progress = ((currentIdx + 1) / questions.length) * 100;
                const userAnswer = userAnswers[currentIdx];

                return (
                    <div className="h-screen flex flex-col items-center justify-center p-6">
                        <div className="glass-panel w-full max-w-3xl h-[85vh] rounded-3xl flex flex-col overflow-hidden animate-fade-in border-0 shadow-2xl">
                            
                            <div className="px-10 py-6 border-b border-gray-100/50 flex justify-between items-center bg-white/40">
                                <span className="font-mono text-xs font-semibold text-gray-400 uppercase tracking-widest">
                                    Question {currentIdx + 1} / {questions.length}
                                </span>
                                <div className="bg-white/60 px-3 py-1 rounded-lg text-xs font-bold text-gray-700 shadow-sm">
                                    Score: {score}
                                </div>
                            </div>
                            
                            <div className="w-full bg-gray-100/50 h-1">
                                <div className="bg-gray-800 h-1 transition-all duration-700 ease-out" style={{width: `${progress}%`}}></div>
                            </div>

                            <div className="flex-1 overflow-y-auto p-10 md:p-14">
                                <h2 className="text-2xl md:text-3xl font-bold text-gray-800 mb-12 leading-tight">{q.text}</h2>
                                
                                <div className="space-y-4">
                                    {q.options.map((opt, i) => {
                                        let btnClass = "smooth-btn w-full text-left p-5 rounded-2xl border flex items-center gap-5 group relative overflow-hidden ";
                                        
                                        if (showFeedback) {
                                            if (i === q.correct) btnClass += "border-green-500 bg-green-50 text-green-900";
                                            else if (i === userAnswer && userAnswer !== 'skipped') btnClass += "border-red-500 bg-red-50 text-red-900";
                                            else btnClass += "border-transparent bg-gray-50/50 opacity-40";
                                        } else {
                                            btnClass += "border-transparent bg-white/60 hover:bg-white hover:border-gray-200 hover:shadow-lg text-gray-600";
                                        }

                                        return (
                                            <button key={i} onClick={() => handleAnswer(i)} disabled={showFeedback} className={btnClass}>
                                                <span className={`w-8 h-8 flex-none flex items-center justify-center rounded-lg text-xs font-bold transition-all duration-500 ${showFeedback && i === q.correct ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-400 group-hover:bg-gray-900 group-hover:text-white'}`}>
                                                    {String.fromCharCode(65 + i)}
                                                </span>
                                                <span className="font-medium text-lg">{opt}</span>
                                            </button>
                                        );
                                    })}
                                </div>

                                {showFeedback && (
                                    <div className="mt-10 p-6 bg-white/60 rounded-2xl border border-gray-100 shadow-sm animate-fade-in backdrop-blur-md">
                                        <div className="flex items-start gap-4">
                                            <div>
                                                <h4 className={`font-bold text-lg mb-1 ${userAnswer === q.correct ? 'text-green-700' : 'text-red-700'}`}>
                                                    {userAnswer === q.correct ? 'Correct' : 'Incorrect'}
                                                </h4>
                                                <p className="text-gray-600 leading-relaxed">{q.rationale}</p>
                                            </div>
                                        </div>
                                    </div>
                                )}
                                <div className="h-24"></div>
                            </div>

                            <div className="p-6 bg-white/60 border-t border-gray-100/50 absolute bottom-0 w-full flex justify-between items-center backdrop-blur-md">
                                {!showFeedback ? (
                                    <button 
                                        onClick={handleSkip}
                                        className="text-gray-400 hover:text-gray-600 text-sm font-medium px-4 py-2 transition-colors flex items-center gap-2"
                                    >
                                        Skip <i className="fas fa-forward text-xs"></i>
                                    </button>
                                ) : <div></div>}

                                <button 
                                    onClick={moveToNext}
                                    className={`smooth-btn bg-gray-900 text-white font-medium py-3 px-10 rounded-full shadow-xl hover:shadow-2xl active:scale-95 ${!showFeedback ? 'invisible' : ''}`}
                                >
                                    Continue
                                </button>
                            </div>
                        </div>
                    </div>
                );
            }

            if (view === 'results') {
                const skippedCount = Object.values(userAnswers).filter(a => a === 'skipped').length;
                const correctCount = score;
                const wrongCount = questions.length - correctCount - skippedCount;
                const hasMistakes = (skippedCount + wrongCount) > 0;

                return (
                    <div className="flex items-center justify-center h-screen p-6">
                        <div className="glass-panel w-full max-w-md p-12 rounded-3xl text-center animate-fade-in relative">
                            <h2 className="text-3xl font-bold text-gray-900 mb-2">Quiz Complete</h2>
                            
                            <div className="text-7xl font-bold text-gray-800 my-8 tracking-tighter">
                                {Math.round((score / questions.length) * 100)}<span className="text-2xl text-gray-400 font-normal">%</span>
                            </div>
                            
                            <div className="flex justify-center gap-6 mb-10 text-sm font-medium text-gray-500 uppercase tracking-widest">
                                <div className="flex flex-col">
                                    <span className="text-green-600 font-bold text-lg">{correctCount}</span>
                                    <span>Right</span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-red-500 font-bold text-lg">{wrongCount}</span>
                                    <span>Wrong</span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-amber-500 font-bold text-lg">{skippedCount}</span>
                                    <span>Skipped</span>
                                </div>
                            </div>
                            
                            <div className="space-y-3 mb-8">
                                {hasMistakes && (
                                    <button 
                                        onClick={startRetry}
                                        className="smooth-btn w-full bg-gray-900 text-white font-medium py-4 rounded-xl shadow-lg hover:shadow-xl transition flex items-center justify-center gap-2"
                                    >
                                        <i className="fas fa-undo"></i> Retry {skippedCount + wrongCount} Mistakes
                                    </button>
                                )}

                                <button 
                                    onClick={() => setView('setup')}
                                    className="smooth-btn w-full bg-white border border-gray-200 text-gray-900 font-medium py-4 rounded-xl hover:bg-gray-50 transition shadow-sm"
                                >
                                    Start New Quiz
                                </button>
                            </div>

                            {/* Add More Section with Liquid Slider */}
                            <div className="mt-4 pt-5 border-t border-gray-100/50 text-left">
                                <div className="mb-3">
                                    <div className="flex justify-between text-[10px] font-semibold text-gray-400 mb-2 uppercase tracking-widest">
                                        <span>Add More</span>
                                        <span>{Math.round(moreQuestions)} Questions</span>
                                    </div>
                                    <GlassSlider
                                        min={1}
                                        max={50}
                                        value={moreQuestions}
                                        onChange={setMoreQuestions}
                                    />
                                </div>
                                <button
                                    onClick={handleAddMoreQuestions}
                                    disabled={addingMore}
                                    className="smooth-btn w-full bg-gray-900 text-white font-medium py-3 rounded-xl shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                    {addingMore ? (
                                        <>
                                            <i className="fas fa-circle-notch fa-spin"></i>
                                            Generating...
                                        </>
                                    ) : (
                                        <>
                                            <i className="fas fa-plus-circle"></i>
                                            Add Questions
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                );
            }
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>
"""

@app.get("/")
async def get_index():
    return HTMLResponse(content=html_content)

@app.post("/generate-quiz")
async def generate_quiz(
        topic: str = Form(""),
        num_questions: int = Form(...),
        file: UploadFile = File(None)
):
    # Safety clamp
    if num_questions < 1: num_questions = 1
    if num_questions > 50: num_questions = 50

    if not topic.strip() and not file:
        raise HTTPException(status_code=400, detail="Please enter a topic or upload a file.")

    url = "https://openrouter.ai/api/v1/chat/completions"

    system_msg = """
    You are a strict JSON Quiz Generator.
    Task: Create a multiple choice quiz.
    Use only the provided CONTEXT text (from the uploaded file or text topic) as your source of truth.
    Do not invent facts that are not present in the CONTEXT.
    OUTPUT RULES:
    1. Return ONLY valid JSON. No markdown.
    2. Structure: [{"text": "Question?", "options": ["A", "B", "C", "D"], "correct": 0, "rationale": "Why?"}]
    """

    # UNIFIED MODEL: QWEN 2.5 VL 72B (Vision + Text)
    model = "qwen/qwen2.5-vl-72b-instruct"

    # PROMPT
    if topic.strip():
        user_content = f"Generate {num_questions} questions about: {topic}"
    else:
        user_content = f"Generate {num_questions} questions based ENTIRELY on the file content below. Do not simply copy and paste the text from the file, but make the quiz based on concepts within the text."

    messages = [{"role": "system", "content": system_msg}]

    if file:
        content = await file.read()
        mime = file.content_type or ""
        filename = (file.filename or "").lower()

        # IMAGE
        if "image" in mime:
            b64 = base64.b64encode(content).decode('utf-8')
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_content},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"}
                    }
                ]
            })

        # PDF
        elif "pdf" in mime or filename.endswith(".pdf"):
            try:
                reader = PdfReader(BytesIO(content))
                text_content = "\n".join(page.extract_text() or "" for page in reader.pages)
                messages.append({"role": "user", "content": f"{user_content}\n\nCONTEXT (PDF):\n{text_content[:25000]}"})
            except Exception as e:
                raise HTTPException(400, f"Error reading PDF: {str(e)}")

        # DOCX (Simple parsing via regex/xml fallback)
        elif "word" in mime or filename.endswith(".docx"):
            try:
                with ZipFile(BytesIO(content)) as docx_zip:
                    with docx_zip.open("word/document.xml") as doc_xml:
                        xml_content = doc_xml.read()
                root = etree.fromstring(xml_content)
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                text_nodes = root.xpath("//w:t/text()", namespaces=ns)
                docx_text = "\n".join(text_nodes)
                messages.append({"role": "user", "content": f"{user_content}\n\nCONTEXT (DOCX):\n{docx_text[:25000]}"})
            except:
                try:
                    # Fallback to UTF-8
                    text = content.decode('utf-8', errors='ignore')
                    messages.append({"role": "user", "content": f"{user_content}\n\nCONTEXT (RAW):\n{text[:25000]}"})
                except:
                    raise HTTPException(400, "DOCX parsing failed. Try PDF or Text.")

        # TEXT
        else:
            text = content.decode('utf-8', errors='ignore')
            messages.append({"role": "user", "content": f"{user_content}\n\nCONTEXT:\n{text[:25000]}"})
    else:
        messages.append({"role": "user", "content": user_content})

    try:
        response = requests.post(
            url,
            # AUTH HEADERS - USES GLOBAL ENV VAR NOW
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "Referer": "http://localhost:8000",
                "X-Title": "QuizGen"
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7
            },
            timeout=180
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        result = response.json()
        content_str = result['choices'][0]['message']['content']

        # ROBUST REGEX JSON PARSING
        json_match = re.search(r'\[.*\]', content_str, flags=re.DOTALL)
        if json_match:
            clean = json_match.group(0)
        else:
            clean = content_str.replace("```json", "").replace("```", "").strip()

        data = json.loads(clean)

        if isinstance(data, dict) and "questions" in data: data = data["questions"]

        # CRASH-PROOF SHUFFLING
        final_questions = []
        for q in data:
            if (
                    "options" not in q or
                    "correct" not in q or
                    not isinstance(q["options"], list)
            ):
                continue

            if q["correct"] >= len(q["options"]) or q["correct"] < 0:
                continue

            opts = q['options']
            correct_txt = opts[q['correct']]
            random.shuffle(opts)

            try:
                new_idx = opts.index(correct_txt)
                q['options'] = opts
                q['correct'] = new_idx
                final_questions.append(q)
            except ValueError:
                continue

        if not final_questions:
            raise HTTPException(500, "Failed to generate valid questions. Try again.")

        return final_questions

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)