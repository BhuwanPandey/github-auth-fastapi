from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from githubkit.versions.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthAppAuthStrategy, OAuthTokenAuthStrategy
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse
from settings import settings
import githubkit

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Add the session middleware
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)


@app.get("/",response_class=HTMLResponse)
async def read_item(request: Request):
    session = request.session
    access_token = session.get("access_token", None)
    try:
        if access_token:
            github = GitHub(OAuthAppAuthStrategy(settings.CLIENT_ID, settings.CLIENT_SECRET))
            user_github = github.with_auth(
                OAuthTokenAuthStrategy(
                settings.CLIENT_ID, settings.CLIENT_SECRET,token=access_token
                )
            )
            resp = user_github.rest.users.get_authenticated()
            user: PublicUser | PrivateUser = resp.parsed_data
            logout = "http://127.0.0.1:8000/logout"
            return templates.TemplateResponse(
                request=request, name="home.html",context={"user":user,"logout":logout}
            )
    except githubkit.exception.RequestFailed:
        session.clear()

    redirect_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.CLIENT_ID}"
        f"&redirect_uri={settings.CallBack_URL}"
        f"&scope=user:email"
        f"&state={settings.SECRET_KEY}"
    )
    return templates.TemplateResponse(
        request=request, name="login.html",context={"redirect_url":redirect_url}
    )


@app.get('/callback')
def callback(req: Request):
    session = req.session
    token = session.get("access_token", None)
    if token:
        return RedirectResponse(url="/")
    code = req.query_params.get('code')
    github = GitHub(OAuthAppAuthStrategy(settings.CLIENT_ID, settings.CLIENT_SECRET))
    auth = github.auth.as_web_user(code).exchange_token(github)
    access_token = auth.token
    session["access_token"] = access_token
    return RedirectResponse(url="/")

@app.get("/logout")
async def logout(request: Request):
    session = request.session
    session.clear()
    return RedirectResponse(url="/")
