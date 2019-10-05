FROM python:2-stretch

ENV USER=citus

RUN groupadd -r ${USER} --gid=1729
RUN useradd -mg ${USER} --uid=1729 --shell=/bin/bash ${USER}

USER ${USER}
WORKDIR /home/${USER}

RUN git clone https://github.com/citusdata/test-automation.git

RUN pip install -r $HOME/test-automation/fabfile/requirements.txt --user

RUN echo 'source ${HOME}/test-automation/cloudformation/fab' >> ${HOME}/.bashrc

# add local bin so that we can use fab
RUN echo 'export PATH=${HOME}/.local/bin/:$PATH' >> ${HOME}/.bashrc

RUN ln -s ${HOME}/test-automation/fabfile ${HOME}/fabfile
