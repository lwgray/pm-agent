# 🧠 How Marcus Works

Let's understand Marcus using a simple analogy: imagine a classroom!

## 📚 The Classroom Analogy

Think of Marcus like this:

- **Marcus** = The Teacher 👩‍🏫
- **AI Workers** = Students 👨‍🎓👩‍🎓
- **GitHub Issues** = Homework Assignments 📝
- **Your Code** = The Class Project 🏗️

## 🔄 The Process

### 1. Teacher Prepares Assignments (You Create Tasks)

You create "assignments" by making GitHub Issues:
```
Issue #1: Create a login page
Issue #2: Add user database
Issue #3: Write tests for login
```

### 2. Students Ask for Work (Workers Request Tasks)

AI workers connect and say "What should I work on?"

```
Backend Developer: "I'm good at databases!"
Frontend Developer: "I can make web pages!"
QA Engineer: "I can write tests!"
```

### 3. Teacher Assigns Homework (Marcus Matches Tasks)

Marcus looks at:
- What each student is good at
- What assignments are available
- Which is most important

Then assigns:
- Backend Developer → "Add user database"
- Frontend Developer → "Create a login page"
- QA Engineer → "Write tests for login"

### 4. Students Do Their Work (Workers Complete Tasks)

Workers:
- Read the assignment
- Do the work
- Report progress ("I'm 50% done!")
- Ask for help if stuck

### 5. Teacher Tracks Progress (Marcus Monitors)

Marcus:
- Watches who's working on what
- Helps when someone's stuck
- Updates the task board
- Shares what's been built

## 🎯 The Smart Parts

### 🧩 Knowledge Sharing

When using GitHub, Marcus is extra smart:

- Worker 1 creates an API endpoint: `/api/login`
- Marcus remembers this
- Worker 2 needs to use login? Marcus says: "Use `/api/login` that Worker 1 made!"

### 🤖 AI-Powered Help

When a worker gets stuck:
1. Worker: "I don't know how to connect to the database"
2. Marcus: "Try using the connection string in config.js, here's an example..."

### 📊 Smart Task Assignment

Marcus assigns tasks based on:
- **Skills** - What the worker is good at
- **Priority** - What's most important
- **Dependencies** - What needs to be done first

## 🏗️ Real Example

Let's say you want to build a todo app:

1. **You create issues**:
   - "Set up database"
   - "Create API endpoints"
   - "Build user interface"
   - "Add authentication"

2. **Workers join**:
   - Backend Dev (good at: databases, APIs)
   - Frontend Dev (good at: UI, React)
   - Full Stack Dev (good at: everything)

3. **Marcus assigns**:
   - Backend Dev → "Set up database" (best match!)
   - Full Stack Dev → "Add authentication" (needs both skills)
   - Frontend Dev → waits for API to be ready

4. **Work happens**:
   - Backend Dev finishes database
   - Marcus tells Frontend Dev: "Database is ready at `postgres://localhost/todos`"
   - Frontend Dev can now build UI

## 📁 What Gets Created

```
Your Project/
├── logs/
│   └── conversations/     # All the "classroom discussions"
├── Your Code/            # What workers build
└── GitHub Issues/        # Task tracking
```

## 💡 Why This Is Cool

1. **No Manual Coordination** - Marcus handles who does what
2. **Knowledge Transfer** - Workers know what others built
3. **Automatic Progress** - Everything is tracked
4. **Smart Help** - AI assists when workers get stuck

## 🔧 Under the Hood

For the curious, here's what actually happens:

1. **MCP Protocol** - Workers and Marcus talk using a standard language
2. **Docker Containers** - Everything runs in isolated boxes
3. **API Connections** - Marcus connects to GitHub/Linear to get/update tasks
4. **AI Analysis** - Uses AI to understand tasks and worker capabilities

## 🎮 Try It Yourself!

Run the demo to see this in action:

```bash
./start.sh demo
```

Watch the logs to see the "classroom" in action:
```bash
docker-compose logs -f pm-agent
```

---

Next: Learn about [Choosing Your Task Board](providers.md) to pick the best option for your project!