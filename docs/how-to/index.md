# PM Agent How-To Guides

Task-oriented guides for common PM Agent operations. Each guide provides step-by-step instructions to accomplish specific tasks.

## 🔧 Troubleshooting

- [**Troubleshoot Common Issues**](troubleshoot-common-issues.md)  
  Diagnose and fix the most common PM Agent problems quickly

## 🚀 Deployment Guides

- [**Deploy with Docker**](deploy-with-docker.md)  
  Deploy PM Agent using Docker for consistent, reproducible environments

- [**Deploy with Python**](deploy-with-python.md)  
  Deploy PM Agent directly using Python for development or lightweight production

- [**Deploy on Kubernetes**](deploy-on-kubernetes.md)  
  Deploy PM Agent on Kubernetes for scalable, production-grade environments

## 🔒 Security

- [**Security Best Practices**](security-best-practices.md)  
  Implement security best practices for PM Agent in production

## 📋 Quick Reference

### Deployment Decision Tree

```
Which deployment method should I use?
├─ Need scalability/HA? → Kubernetes
├─ Want isolation/consistency? → Docker
└─ Development/debugging? → Python
```

### Time Estimates

| Guide | Time Required | Difficulty |
|-------|--------------|------------|
| Troubleshooting | 5-15 min | Easy |
| Docker Deployment | 10-20 min | Medium |
| Python Deployment | 5-15 min | Easy |
| Kubernetes Deployment | 30-45 min | Hard |
| Security Setup | 30-60 min | Medium |

## 🎯 Common Tasks

### First Time Setup
1. Start with [Deploy with Docker](deploy-with-docker.md) for the easiest setup
2. Follow [Security Best Practices](security-best-practices.md) before production
3. Keep [Troubleshoot Common Issues](troubleshoot-common-issues.md) handy

### Production Deployment
1. Choose between [Kubernetes](deploy-on-kubernetes.md) or [Docker](deploy-with-docker.md)
2. Implement all [Security Best Practices](security-best-practices.md)
3. Set up monitoring and backups

### Development Setup
1. Use [Deploy with Python](deploy-with-python.md) for local development
2. Enable debug mode for easier troubleshooting
3. Use hot-reload for faster iteration

## 📚 Related Documentation

- [Getting Started Guide](/getting-started) - New to PM Agent? Start here
- [Tutorials](/tutorials) - Learn PM Agent through examples
- [API Reference](/reference/api) - Detailed API documentation
- [Concepts](/concepts) - Understand PM Agent architecture

## 💡 Tips

- Always test deployments in a staging environment first
- Keep your API keys secure - never commit them to git
- Enable logging and monitoring from day one
- Regular backups are essential for production
- Update PM Agent regularly for security patches

## 🆘 Need Help?

If these guides don't solve your problem:

1. Check the [FAQ](/reference/faq)
2. Search [GitHub Issues](https://github.com/your-org/pm-agent/issues)
3. Ask in [Discord Community](https://discord.gg/pm-agent)
4. Create a [GitHub Issue](https://github.com/your-org/pm-agent/issues/new)